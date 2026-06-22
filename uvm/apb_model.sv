`ifndef APB_MODEL__SV
`define APB_MODEL__SV

class apb_model extends uvm_component;

   uvm_blocking_get_port #(apb_transaction)  port;
   uvm_analysis_port #(apb_transaction)  ap;
   logic [31:0] mirror  [15:0];
   virtual apb_if vif;

   function new(string name, uvm_component parent);
      super.new(name, parent);
   endfunction

   extern function void build_phase(uvm_phase phase);
   extern virtual task run_phase(uvm_phase phase);

   `uvm_component_utils(apb_model)
endclass

function void apb_model::build_phase(uvm_phase phase);
   super.build_phase(phase);
   port = new("port", this);
   ap = new("ap", this);
   if(!uvm_config_db#(virtual apb_if)::get(this, "", "vif", vif))
      `uvm_fatal("apb_model", "virtual interface must be set for vif!!!")
endfunction

task apb_model::run_phase(uvm_phase phase);
   apb_transaction tr;
   apb_transaction new_tr;
   super.run_phase(phase);
   fork
      forever begin
         @(negedge vif.prst_n);
         for(int i = 0; i < 16; i++) mirror[i] = 0;
      end
   join_none
   forever begin
      port.get(tr);
      new_tr = new("new_tr");
      new_tr.addr = tr.addr;
      new_tr.write = tr.write;
      if(tr.write) begin
         mirror[tr.addr[5:2]] = tr.data;
         new_tr.data = tr.data;
      end
      else begin
         new_tr.data = mirror[tr.addr[5:2]];
      end
      ap.write(new_tr);
   end
endtask
`endif
