interface apb_if(input logic pclk);
    logic        prst_n;
    logic [31:0] paddr;
    logic        psel;
    logic        penable;
    logic        pwrite;
    logic [31:0] pwdata;
    logic [31:0] prdata;
    logic        pready;
    logic        pslverr;

    clocking cb_master @(posedge pclk);
        output paddr, psel, penable, pwrite, pwdata;
        input  prdata, pready, pslverr;
    endclocking

    clocking cb_slave @(posedge pclk);
        input  paddr, psel, penable, pwrite, pwdata;
        output prdata, pready, pslverr;
    endclocking

    clocking cb_monitor @(posedge pclk);
        input paddr, psel, penable, pwrite, pwdata;
        input prdata, pready, pslverr;
    endclocking

    modport master (
        output paddr, psel, penable, pwrite, pwdata,
        input  prdata, pready, pslverr
    );
    modport slave (
        input  paddr, psel, penable, pwrite, pwdata,
        output prdata, pready, pslverr
    );
    modport master_cb  (clocking cb_master, input prst_n);
    modport slave_cb   (clocking cb_slave,  input prst_n);
    modport monitor_cb (clocking cb_monitor, input prst_n);

    task do_reset(int cycles = 5);
        prst_n = 1'b0;
        repeat(cycles) @(posedge pclk);
        prst_n = 1'b1;
    endtask

endinterface
