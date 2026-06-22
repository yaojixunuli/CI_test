`ifndef APB_COVERAGE__SV
`define APB_COVERAGE__SV

// 功能覆盖率收集器：订阅 master monitor 的 analysis port，
// 每收到一笔 apb_transaction 就采样一次 covergroup。
class apb_coverage extends uvm_subscriber #(apb_transaction);

   apb_transaction tr;

   covergroup apb_cg;
      option.per_instance = 1;

      // 读/写方向
      cp_dir : coverpoint tr.write {
         bins write = {1};
         bins read  = {0};
      }

      // 访问地址：slave 用 paddr[5:2] 寻址 16 个寄存器
      cp_addr : coverpoint tr.addr[5:2] {
         bins addr[] = {[0:15]};
      }

      // 数据典型值：全 0、全 1、其余
      cp_data : coverpoint tr.data {
         bins zero   = {32'h0000_0000};
         bins ones   = {32'hFFFF_FFFF};
         bins others = default;
      }

      // 交叉：每个地址都覆盖到读和写
      cx_dir_addr : cross cp_dir, cp_addr;
   endgroup

   `uvm_component_utils(apb_coverage)

   function new(string name = "apb_coverage", uvm_component parent = null);
      super.new(name, parent);
      apb_cg = new();
   endfunction

   // uvm_subscriber 自带 analysis_export，每笔事务回调 write()
   virtual function void write(apb_transaction t);
      tr = t;
      apb_cg.sample();
   endfunction

   virtual function void report_phase(uvm_phase phase);
      super.report_phase(phase);
      `uvm_info("apb_coverage",
                $sformatf("Functional coverage = %0.2f%%", apb_cg.get_inst_coverage()),
                UVM_LOW)
   endfunction

endclass

`endif
