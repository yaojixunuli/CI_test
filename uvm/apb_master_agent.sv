`ifndef APB_MASTER_AGENT__SV
`define APB_MASTER_AGENT__SV

class apb_master_agent extends uvm_agent ;
   apb_sequencer  sqr;
   apb_driver     drv;
   apb_monitor    mon;
   
   uvm_analysis_port #(apb_transaction)  ap;
   
   function new(string name, uvm_component parent);
      super.new(name, parent);
   endfunction 
   
   extern virtual function void build_phase(uvm_phase phase);
   extern virtual function void connect_phase(uvm_phase phase);

   `uvm_component_utils(apb_master_agent)
endclass 


function void apb_master_agent::build_phase(uvm_phase phase);
    super.build_phase(phase);
    sqr = apb_sequencer::type_id::create("sqr", this);
    drv = apb_driver::type_id::create("drv", this);
    mon = apb_monitor::type_id::create("mon", this);
endfunction 

function void apb_master_agent::connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    drv.seq_item_port.connect(sqr.seq_item_export);
    ap = mon.ap;
endfunction

`endif

