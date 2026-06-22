`ifndef APB_SEQUENCE_CASE0__SV
`define APB_SEQUENCE_CASE0__SV

class apb_sequence_case0 extends uvm_sequence #(apb_transaction);
    function new(string name= "apb_sequence_case0");
        super.new(name);
    endfunction

    virtual task body();
        apb_transaction tr;
        bit [31:0] addr_i;
        bit [31:0] data_i;
        if(get_starting_phase() != null)
            get_starting_phase().raise_objection(this);

        // 覆盖低半区 addr[5:2] = 0~7：每个地址先写后读
        // → 命中 cp_addr[0:7]、cp_dir 读写、cx_dir_addr 中这 8 个地址的读+写
        for (int i = 0; i < 8; i++) begin
            addr_i = i << 2;                          // 0x00, 0x04, ... 0x1C
            data_i = (i == 0) ? 32'h0000_0000         // 命中 cp_data.zero
                              : (32'hDEAD_0000 + i);  // 命中 cp_data.others
            `uvm_do_with(tr, { tr.write == 1; tr.addr == addr_i; tr.data == data_i; })
            `uvm_do_with(tr, { tr.write == 0; tr.addr == addr_i; })
        end

        if(get_starting_phase() != null)
            get_starting_phase().drop_objection(this);
    endtask

    `uvm_object_utils(apb_sequence_case0)
endclass


class apb_test_case0 extends apb_base_test;

   function new(string name = "apb_test_case0", uvm_component parent = null);
      super.new(name,parent);
   endfunction 

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);

        uvm_config_db#(uvm_object_wrapper)::set(this,
                                                "env.master_agent.sqr.run_phase",
                                                "default_sequence",
                                                apb_sequence_case0::type_id::get());
    endfunction

   `uvm_component_utils(apb_test_case0)
endclass

`endif
