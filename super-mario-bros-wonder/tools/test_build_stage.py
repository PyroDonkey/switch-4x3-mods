"""Synthetic BYML tests for the guarded pooled-Gyaml rename; no game files required."""
import copy
import struct
import unittest

from build_stage import replace_actor_gyaml
from byml import parse


ORIGINAL = 'PillarA01'
REPLACEMENT = 'PillarA00'
ERRORS = (AssertionError, ValueError, KeyError)


def u24(value):
    return value.to_bytes(3, 'little')


class Fixture:
    """Encode only the little-endian BYML types needed by these tests."""

    def __init__(self, actors=None, metadata=None, extra_strings=()):
        if actors is None:
            actors = ((1, ORIGINAL), (2, ORIGINAL))
        self.tree = {'Actors': [{'Gyaml': name, 'Hash': h} for h, name in actors]}
        if metadata is not None:
            self.tree['Metadata'] = metadata

        keys = set()
        strings = {'Alpha', ORIGINAL, 'Zulu'}

        def collect(value):
            if isinstance(value, dict):
                keys.update(value)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
            elif isinstance(value, str):
                strings.add(value)

        collect(self.tree)
        self.keys = sorted(keys)
        self.strings = sorted(list(strings) + list(extra_strings))
        self.key_indices = {key: i for i, key in enumerate(self.keys)}
        self.string_indices = {}
        for i, value in enumerate(self.strings):
            self.string_indices.setdefault(value, i)

        self.data = bytearray(16)
        keys_off = self.append(self.string_table(self.keys))
        self.strings_off = self.append(self.string_table(self.strings))
        kind, root_off = self.encode(self.tree)
        assert kind == 0xC1
        struct.pack_into('<2sHIII', self.data, 0, b'YB', 7, keys_off, self.strings_off, root_off)

    def append(self, payload):
        self.data.extend(bytes((-len(self.data)) % 4))
        offset = len(self.data)
        self.data.extend(payload)
        return offset

    @staticmethod
    def string_table(values):
        payload = bytearray()
        offsets = []
        start = 4 + 4 * (len(values) + 1)
        for value in values:
            offsets.append(start + len(payload))
            payload.extend(value.encode('utf-8') + b'\0')
        offsets.append(start + len(payload))
        return (b'\xC2' + u24(len(values))
                + struct.pack('<' + 'I' * len(offsets), *offsets) + payload)

    def encode(self, value):
        if isinstance(value, str):
            return 0xA0, self.string_indices[value]
        if isinstance(value, int):
            return 0xD3, value
        if isinstance(value, dict):
            entries = bytearray()
            for key, child in sorted(value.items()):
                kind, raw = self.encode(child)
                entries.extend(u24(self.key_indices[key]) + bytes([kind]) + struct.pack('<I', raw))
            return 0xC1, self.append(b'\xC1' + u24(len(value)) + entries)
        if isinstance(value, list):
            entries = [self.encode(child) for child in value]
            types = bytes(kind for kind, _ in entries)
            slots = b''.join(struct.pack('<I', raw) for _, raw in entries)
            return 0xC0, self.append(b'\xC0' + u24(len(entries)) + types
                                     + bytes((-len(entries)) % 4) + slots)
        raise TypeError(type(value))

    def string_offset_slot(self, value):
        return self.strings_off + 4 + 4 * self.string_indices[value]

    def string_start(self, value):
        relative = struct.unpack_from('<I', self.data, self.string_offset_slot(value))[0]
        return self.strings_off + relative

    def alias_string_storage(self, value, owner, within=0):
        relative = self.string_start(owner) + within - self.strings_off
        struct.pack_into('<I', self.data, self.string_offset_slot(value), relative)


class ReplaceActorGyamlTests(unittest.TestCase):
    def assert_rename(self, fixture):
        before = bytes(fixture.data)
        expected = copy.deepcopy(parse(before))
        self.assertEqual(expected, fixture.tree)
        for actor in expected['Actors']:
            if actor['Hash'] in (1, 2):
                actor['Gyaml'] = REPLACEMENT

        changed_byte = fixture.string_start(ORIGINAL) + len(ORIGINAL.encode('utf-8')) - 1
        changed = replace_actor_gyaml(fixture.data, (1, 2), ORIGINAL, REPLACEMENT)
        self.assertIsInstance(changed, set)
        self.assertEqual(len(fixture.data), len(before))
        actual = {i for i, (old, new) in enumerate(zip(before, fixture.data)) if old != new}
        self.assertEqual(actual, {changed_byte})
        self.assertEqual(changed, actual)
        self.assertEqual(before[changed_byte], ord('1'))
        self.assertEqual(fixture.data[changed_byte], ord('0'))
        # The exact diff also proves that indices, offsets, NULs and padding stayed unchanged.
        self.assertEqual(parse(fixture.data), expected)

    def assert_rejected(self, fixture, hashes=(1, 2), original=ORIGINAL, replacement=REPLACEMENT):
        before = bytes(fixture.data)
        with self.assertRaises(ERRORS):
            replace_actor_gyaml(fixture.data, hashes, original, replacement)
        self.assertEqual(bytes(fixture.data), before, 'rejected edits must not mutate the input')

    def test_rename_shared_source_once(self):
        self.assert_rename(Fixture())

    def test_unrelated_actor_and_nested_metadata_are_preserved(self):
        fixture = Fixture(
            actors=((1, ORIGINAL), (2, ORIGINAL), (3, 'OtherA01')),
            metadata={'Nested': [{'Alias': 'OtherA01', 'Number': 42}]},
        )
        self.assert_rename(fixture)

    def test_missing_selected_hash_is_rejected(self):
        self.assert_rejected(Fixture(), hashes=(1, 99))

    def test_duplicate_requested_hash_is_rejected(self):
        self.assert_rejected(Fixture(), hashes=(1, 1, 2))

    def test_duplicate_actor_hash_is_rejected(self):
        self.assert_rejected(Fixture(actors=((1, ORIGINAL), (1, ORIGINAL), (2, ORIGINAL))))

    def test_wrong_original_gyaml_name_is_rejected(self):
        self.assert_rejected(Fixture(actors=((1, 'OtherA01'), (2, ORIGINAL))))

    def test_non_string_gyaml_type_is_rejected(self):
        self.assert_rejected(Fixture(actors=((1, 7), (2, ORIGINAL))))

    def test_unequal_ascii_byte_length_is_rejected(self):
        self.assert_rejected(Fixture(), replacement='PillarA000')

    def test_equal_character_count_with_unequal_utf8_length_is_rejected(self):
        replacement = 'PillarA0\u00e9'
        self.assertEqual(len(replacement), len(ORIGINAL))
        self.assertNotEqual(len(replacement.encode('utf-8')), len(ORIGINAL.encode('utf-8')))
        self.assert_rejected(Fixture(), replacement=replacement)

    def test_third_actor_consumer_is_rejected(self):
        self.assert_rejected(Fixture(actors=((1, ORIGINAL), (2, ORIGINAL), (3, ORIGINAL))))

    def test_nested_non_actor_consumer_is_rejected(self):
        self.assert_rejected(Fixture(metadata={'Nested': [{'Alias': ORIGINAL}]}))

    def test_duplicate_original_value_string_entry_is_rejected(self):
        self.assert_rejected(Fixture(extra_strings=(ORIGINAL,)))

    def test_replacement_already_in_string_table_is_rejected(self):
        self.assert_rejected(Fixture(extra_strings=(REPLACEMENT,)))

    def test_rename_that_breaks_string_sorting_is_rejected(self):
        # PillarA00a sorts before the source, but after its proposed replacement.
        self.assert_rejected(Fixture(extra_strings=('PillarA00a',)))

    def test_duplicate_value_string_storage_is_rejected(self):
        fixture = Fixture(extra_strings=('PillarA02',))
        fixture.alias_string_storage('PillarA02', ORIGINAL)
        self.assert_rejected(fixture)

    def test_overlapping_suffix_string_storage_is_rejected(self):
        fixture = Fixture(extra_strings=('01',))
        fixture.alias_string_storage('01', ORIGINAL, within=len('PillarA'))
        # Decoded values and their sorting are unchanged; the source's last byte is aliased.
        self.assertEqual(parse(fixture.data), fixture.tree)
        self.assert_rejected(fixture)


class EventEditsTests(unittest.TestCase):
    def test_edits_by_flow_groups_multiple_edits_on_same_flow(self):
        from build_stage import edits_by_flow, EVENT_EDITS
        grouped = edits_by_flow()
        self.assertIn('CourseDemo_PreFinalBattle', grouped)
        edits = grouped['CourseDemo_PreFinalBattle']
        self.assertEqual(len(edits), 2)
        names = [e[0] for e in edits]
        self.assertEqual(names, ['Event26', 'Event50'])
        self.assertEqual(edits[0], ('Event26', 'TargetYpos', 0x2A80, 27.5, 28.75))
        self.assertEqual(edits[1], ('Event50', 'TargetYpos', 0x2D90, 27.5, 28.75))

    def test_event_edits_float_packing(self):
        buf = bytearray(0x3000)
        struct.pack_into('<f', buf, 0x2A80, 27.5)
        struct.pack_into('<f', buf, 0x2D90, 27.5)
        self.assertEqual(struct.unpack_from('<f', buf, 0x2A80)[0], 27.5)
        self.assertEqual(struct.unpack_from('<f', buf, 0x2D90)[0], 27.5)
        struct.pack_into('<f', buf, 0x2A80, 28.75)
        struct.pack_into('<f', buf, 0x2D90, 28.75)
        self.assertEqual(struct.unpack_from('<f', buf, 0x2A80)[0], 28.75)
        self.assertEqual(struct.unpack_from('<f', buf, 0x2D90)[0], 28.75)


if __name__ == '__main__':
    unittest.main()
