module apb_slave (
    input logic pclk,prst_n,
    apb_if.slave apb
);
    reg [31:0] mem  [15:0];

    always_ff @( posedge pclk or negedge  prst_n) begin
        if(!prst_n)begin
            for(int i=0;i<16;i++) mem[i] = 'd0;
        end
        else begin
            if(apb.psel && apb.penable)begin
                if(apb.pwrite)
                    mem[apb.paddr[5:2]] <= apb.pwdata;
            end
        end
    end

    always_comb begin
    if(apb.psel && !apb.pwrite)
        apb.prdata = mem[apb.paddr[5:2]];
    else
        apb.prdata = '0;
    end

    assign apb.pready = 1;
    assign apb.pslverr = 0;
    
endmodule