`ifndef APB_SLAVE_AGENT__SV
`define APB_SLAVE_AGENT__SV

class apb_slave_agent extends uvm_agent ;
   apb_monitor    mon;
   
   uvm_analysis_port #(apb_transaction)  ap;
   
   function new(string name, uvm_component parent);
      super.new(name, parent);
   endfunction
   
   extern virtual function void build_phase(uvm_phase phase);
   extern virtual function void connect_phase(uvm_phase phase);

   `uvm_component_utils(apb_slave_agent)
endclass 

function void apb_slave_agent::build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon = apb_monitor::type_id::create("mon", this);
endfunction 

function void apb_slave_agent::connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    ap = mon.ap;
endfunction

`endif
