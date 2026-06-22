`ifndef APB_SEQUENCE_CASE1__SV
`define APB_SEQUENCE_CASE1__SV

class apb_sequence_case1 extends uvm_sequence #(apb_transaction);
    virtual apb_if vif;

    function new(string name= "apb_sequence_case1");
        super.new(name);
    endfunction

    virtual task body();
        apb_transaction tr;
        bit [31:0] addr_i;
        bit [31:0] data_i;
        if(get_starting_phase() != null)
            get_starting_phase().raise_objection(this);

        // 覆盖高半区 addr[5:2] = 8~15：每个地址先写后读
        // → 命中 cp_addr[8:15]、cx_dir_addr 中这 8 个地址的读+写
        for (int i = 8; i < 16; i++) begin
            addr_i = i << 2;                          // 0x20, 0x24, ... 0x3C
            data_i = (i == 15) ? 32'hFFFF_FFFF        // 命中 cp_data.ones
                               : (32'hBEEF_0000 + i); // 命中 cp_data.others
            `uvm_do_with(tr, { tr.write == 1; tr.addr == addr_i; tr.data == data_i; })
            `uvm_do_with(tr, { tr.write == 0; tr.addr == addr_i; })
        end

        // ---- 以下为原有的复位功能验证（保留）----
        if(!uvm_config_db#(virtual apb_if)::get(null, "uvm_test_top", "vif", vif))
            `uvm_fatal("SEQ_RESET", "No vif found in config_db")
        #10;
        vif.do_reset(5);

        //复位后读回，期望值全为0
        `uvm_do_with(tr, { write == 0; addr == 32'h0000_0000; })
        `uvm_do_with(tr, { write == 0; addr == 32'h0000_003C; })

        // 3. 测试尾地址写全0
        `uvm_do_with(tr, { tr.write == 1; tr.addr == 32'h0000_003C; tr.data == 32'h8765_4321; })
        `uvm_do_with(tr, { tr.write == 0; tr.addr == 32'h0000_003C; })

        // 4. 测试首地址写全1
        `uvm_do_with(tr, { tr.write == 1; tr.addr == 32'h0000_0000; tr.data == 32'hFFFF_FFFF; })
        `uvm_do_with(tr, { tr.write == 0; tr.addr == 32'h0000_0000; })

        if(get_starting_phase() != null) 
            get_starting_phase().drop_objection(this);
    endtask

    `uvm_object_utils(apb_sequence_case1)
endclass


class apb_test_case1 extends apb_base_test;

   function new(string name = "apb_test_case1", uvm_component parent = null);
      super.new(name,parent);
   endfunction 

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);

        uvm_config_db#(uvm_object_wrapper)::set(this,
                                                "env.master_agent.sqr.run_phase",
                                                "default_sequence",
                                                apb_sequence_case1::type_id::get());
    endfunction

   `uvm_component_utils(apb_test_case1)
endclass

`endif
