`ifndef APB_SEQUENCE__SV
`define APB_SEQUENCE__SV

class apb_sequence extends uvm_sequence #(apb_transaction);
    function new(string name= "apb_sequence");
        super.new(name);
    endfunction

    virtual task body();
        apb_transaction tr;
        if(get_starting_phase() != null)
            get_starting_phase().raise_objection(this);

        `uvm_do_with(tr, { tr.write == 1; tr.addr == 32'h0000_0000; tr.data == 32'hDEAD_BEEF; })
        #100;

        // 读操作：同一地址
        `uvm_do_with(tr, { tr.write == 0; tr.addr == 32'h0000_0000; })
        #100;

        // 再写一个不同的地址
        `uvm_do_with(tr, { tr.write == 1; tr.addr == 32'h0000_0004; tr.data == 32'h1234_5678; })
        #100;

        // 读该地址
        `uvm_do_with(tr, { tr.write == 0; tr.addr == 32'h0000_0004; })
        #100;

        if(get_starting_phase() != null) 
            get_starting_phase().drop_objection(this);
    endtask

    `uvm_object_utils(apb_sequence)
endclass
`endif
