`ifndef APB_ENV__SV
`define APB_ENV__SV

class apb_env extends uvm_env;

   apb_master_agent  master_agent;
   apb_slave_agent   slave_agent;
   apb_model         model;
   apb_scoreboard    scoreboard;
   apb_coverage      coverage;
   
   uvm_tlm_analysis_fifo #(apb_transaction) m_agt_mdl_fifo;
   uvm_tlm_analysis_fifo #(apb_transaction) m_mdl_scb_fifo;
   uvm_tlm_analysis_fifo #(apb_transaction) s_mdl_scb_fifo;
   
   function new(string name = "apb_env", uvm_component parent);
      super.new(name, parent);
   endfunction

   virtual function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      master_agent = apb_master_agent::type_id::create("master_agent", this);
      slave_agent = apb_slave_agent::type_id::create("slave_agent", this);
      scoreboard = apb_scoreboard::type_id::create("scoreboard", this);
      model = apb_model::type_id::create("model", this);
      coverage = apb_coverage::type_id::create("coverage", this);

      m_agt_mdl_fifo = new("m_agt_mdl_fifo", this);
      m_mdl_scb_fifo = new("m_mdl_scb_fifo", this);
      s_mdl_scb_fifo = new("s_mdl_scb_fifo", this);
   endfunction

   extern virtual function void connect_phase(uvm_phase phase);
   
   `uvm_component_utils(apb_env)
endclass

function void apb_env::connect_phase(uvm_phase phase);
   super.connect_phase(phase);

   master_agent.ap.connect(m_agt_mdl_fifo.analysis_export);
   model.port.connect(m_agt_mdl_fifo.blocking_get_export);

   master_agent.ap.connect(coverage.analysis_export);

   model.ap.connect(m_mdl_scb_fifo.analysis_export);
   scoreboard.exp_port.connect(m_mdl_scb_fifo.blocking_get_export);

   slave_agent.ap.connect(s_mdl_scb_fifo.analysis_export);
   scoreboard.act_port.connect(s_mdl_scb_fifo.blocking_get_export); 
endfunction

`endif
