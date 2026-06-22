`ifndef APB_DRIVER__SV
`define APB_DRIVER__SV

class apb_driver extends uvm_driver#(apb_transaction);

   virtual apb_if vif;

   `uvm_component_utils(apb_driver)
   function new(string name = "apb_driver", uvm_component parent = null);
      super.new(name, parent);
   endfunction

   virtual function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if(!uvm_config_db#(virtual apb_if)::get(this, "", "vif", vif))
         `uvm_fatal("apb_driver", "virtual interface must be set for vif!!!")
   endfunction

   extern task run_phase(uvm_phase phase);
   extern task drive_one_pkt(apb_transaction tr);
endclass

task apb_driver::run_phase(uvm_phase phase);
   vif.cb_master.psel    <= 1'b0;
   vif.cb_master.penable <= 1'b0;
   wait(vif.prst_n === 1'b1);
   @(vif.cb_master);

   forever begin
      fork
         begin : drive_seq
            seq_item_port.get_next_item(req);
            drive_one_pkt(req);
            seq_item_port.item_done();
         end
         begin : detect_reset
            @(negedge vif.prst_n);
            vif.cb_master.psel    <= 1'b0;
            vif.cb_master.penable <= 1'b0;
            disable drive_seq;
         end
      join_any
      disable fork;
      wait(vif.prst_n === 1'b1);
      @(vif.cb_master);
   end
endtask

task apb_driver::drive_one_pkt(apb_transaction tr);
    // SETUP
    vif.cb_master.paddr   <= tr.addr;
    vif.cb_master.pwrite  <= tr.write;
    vif.cb_master.pwdata  <= tr.data;
    vif.cb_master.psel    <= 1'b1;
    vif.cb_master.penable <= 1'b0;
    @(vif.cb_master);

    // ACCESS
    vif.cb_master.penable <= 1'b1;
    @(vif.cb_master);
    while (!vif.cb_master.pready) @(vif.cb_master);

    // End of transfer
    vif.cb_master.psel    <= 1'b0;
    vif.cb_master.penable <= 1'b0;
    @(vif.cb_master);
endtask

`endif
