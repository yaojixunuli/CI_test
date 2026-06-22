`ifndef APB_MONITOR__SV
`define APB_MONITOR__SV

class apb_monitor extends uvm_monitor;

   virtual apb_if vif;

   uvm_analysis_port #(apb_transaction)  ap;

   `uvm_component_utils(apb_monitor)
   function new(string name = "apb_monitor", uvm_component parent = null);
      super.new(name, parent);
   endfunction

   virtual function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if(!uvm_config_db#(virtual apb_if)::get(this, "", "vif", vif))
         `uvm_fatal("apb_monitor", "virtual interface must be set for vif!!!")
      ap = new("ap", this);
   endfunction

   extern task run_phase(uvm_phase phase);
   extern task collect_one_pkt(apb_transaction tr);
endclass

task apb_monitor::run_phase(uvm_phase phase);
   apb_transaction tr;
   forever begin
      tr = new("tr");
      collect_one_pkt(tr);
      ap.write(tr);
   end
endtask

task apb_monitor::collect_one_pkt(apb_transaction tr);
    forever begin
        @(vif.cb_monitor);
        if(vif.prst_n === 1'b1 && vif.cb_monitor.psel && vif.cb_monitor.penable && vif.cb_monitor.pready) begin
            tr.addr  = vif.cb_monitor.paddr;
            tr.write = vif.cb_monitor.pwrite;
            if(tr.write)
                tr.data = vif.cb_monitor.pwdata;
            else
                tr.data = vif.cb_monitor.prdata;
            return;
        end
    end
endtask

`endif
