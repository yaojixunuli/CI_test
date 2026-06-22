`timescale 1ns/1ps

import uvm_pkg::*;
import apb_pkg::*;

module top_tb;

   logic pclk;

   apb_if vif(pclk);

   apb_slave dut (
      .pclk    (pclk),
      .prst_n  (vif.prst_n),
      .apb     (vif)
   );

   initial begin
      pclk = 0;
      forever #5 pclk = ~pclk;
   end

   initial begin
      vif.prst_n = 0;
      #20 vif.prst_n = 1;
   end

   initial begin
      $fsdbDumpfile("top_tb.fsdb");
      $fsdbDumpvars(0, top_tb, "+all");
   end

   initial begin
      uvm_config_db#(virtual apb_if)::set(null, "uvm_test_top.env.master_agent.drv", "vif", vif);
      uvm_config_db#(virtual apb_if)::set(null, "uvm_test_top.env.master_agent.mon", "vif", vif);
      uvm_config_db#(virtual apb_if)::set(null, "uvm_test_top.env.slave_agent.mon", "vif", vif);
      uvm_config_db#(virtual apb_if)::set(null, "uvm_test_top.env.model", "vif", vif);
      uvm_config_db#(virtual apb_if)::set(null, "uvm_test_top", "vif", vif);
   end

   initial begin
      run_test();
   end

endmodule
