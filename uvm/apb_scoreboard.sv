`ifndef APB_SCOREBOARD__SV
`define APB_SCOREBOARD__SV

class apb_scoreboard extends uvm_scoreboard;
    apb_transaction  expect_queue[$];
    apb_transaction  actual_queue[$];
    uvm_blocking_get_port #(apb_transaction)  exp_port;
    uvm_blocking_get_port #(apb_transaction)  act_port;

    function new(string name, uvm_component parent = null);
        super.new(name, parent);
    endfunction
    extern virtual function void build_phase(uvm_phase phase);
    extern virtual task run_phase(uvm_phase phase);
    `uvm_component_utils(apb_scoreboard)
endclass

function void apb_scoreboard::build_phase(uvm_phase phase);
    super.build_phase(phase);
    exp_port = new("exp_port", this);
    act_port = new("act_port", this);
endfunction

task apb_scoreboard::run_phase(uvm_phase phase);
    apb_transaction get_expect, get_actual, tmp_tran;
    bit result;
    super.run_phase(phase);

    fork
        forever begin
            exp_port.get(get_expect);
            expect_queue.push_back(get_expect);
        end
        forever begin
            act_port.get(get_actual);
            actual_queue.push_back(get_actual);
        end
        forever begin
            wait(expect_queue.size() > 0 && actual_queue.size() > 0);
            tmp_tran   = expect_queue.pop_front();
            get_actual = actual_queue.pop_front();
            result = get_actual.compare(tmp_tran);
            if(result) begin
                `uvm_info("apb_scoreboard",$sformatf("Compare SUCCESSFULLY addr=0x%0h write=%0b data=0x%0h",
                    tmp_tran.addr, tmp_tran.write, tmp_tran.data), UVM_LOW);
            end
            else begin
                `uvm_error("apb_scoreboard", "Compare FAILED");
                `uvm_info("apb_scoreboard", $sformatf("  expect: addr=0x%0h write=%0b data=0x%0h",
                    tmp_tran.addr, tmp_tran.write, tmp_tran.data), UVM_NONE)
                `uvm_info("apb_scoreboard", $sformatf("  actual: addr=0x%0h write=%0b data=0x%0h",
                    get_actual.addr, get_actual.write, get_actual.data), UVM_NONE)
            end
        end
    join
endtask
`endif
