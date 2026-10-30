// Decompile the functions containing the given addresses (hex, comma separated in script args).
// Function starts are found by walking back to the nearest "stp x29, x30, [sp, #-N]!" or
// "sub sp, sp, #N" prologue when no function exists yet.
// @category AAR
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;

public class DecompileAt extends GhidraScript {
    private Address findStart(Address a) throws Exception {
        Address cur = a;
        for (int i = 0; i < 4000; i++) {
            int w = getInt(cur);
            // stp x29, x30, [sp, #imm]! (pre-index) : 0xA9800000 family with Rt=29, Rt2=30, Rn=31
            if ((w & 0xFFC07FFF) == 0xA9807BFD) return cur;
            // sub sp, sp, #imm (64-bit) as first instruction of a leaf with large frame
            if ((w & 0xFF8003FF) == 0xD10003FF && i > 0) {
                int prev = getInt(cur.subtract(4));
                if (prev == 0xD65F03C0 /* ret */ || (prev & 0xFC000000) == 0x14000000 /* b */) return cur;
            }
            cur = cur.subtract(4);
        }
        return a;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (String s : String.join(",", args).split(",")) {
            Address a = toAddr(Long.parseLong(s.trim(), 16));
            Function f = getFunctionContaining(a);
            if (f == null) {
                Address st = findStart(a);
                new DisassembleCommand(st, null, true).applyTo(currentProgram, monitor);
                new CreateFunctionCmd(st).applyTo(currentProgram, monitor);
                f = getFunctionAt(st);
            }
            if (f == null) { println("NO FUNCTION for " + a); continue; }
            DecompileResults r = di.decompileFunction(f, 120, monitor);
            println("===== function " + f.getEntryPoint() + " (contains " + a + ") =====");
            println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : ("decompile failed: " + r.getErrorMessage()));
        }
        di.dispose();
    }
}
