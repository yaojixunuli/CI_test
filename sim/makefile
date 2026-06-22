.PHONY: all com case0 case1 cov verdi clean

# 代码覆盖率类型：行/条件/翻转/FSM/分支/断言
CM = -cm line+cond+tgl+fsm+branch+assert
CM_NAME = -cm_name $(TEST)

all: com case0 verdi

com:
	vcs -f filelist.f \
		-timescale=1ns/1ps \
		-full64 +v2k -sverilog -Mupdate -ntb_opts uvm-1.2\
		-debug_acc+all -debug_region+cell+encrypt \
		$(CM) -cm_dir ./cov.vdb \
		-l vcs.log

case0:
	./simv +UVM_TESTNAME=apb_test_case0 +UVM_VERDI_TRACE \
		$(CM) -cm_name case0 -cm_dir ./cov.vdb -l sim.log

case1:
	./simv +UVM_TESTNAME=apb_test_case1 +UVM_VERDI_TRACE \
		$(CM) -cm_name case1 -cm_dir ./cov.vdb -l sim.log

# 合并所有用例覆盖率并生成 HTML 报告（urgReport/dashboard.html）
cov:
	urg -dir ./cov.vdb -report urgReport -format both

verdi:
	verdi -sv -f filelist.f -ssf top_tb.fsdb -ssf top_tb_tr.fsdb -play verdi.tcl &
#---------------------------------------------------------------
clean:
	rm -rf csrc DVEfiles novas* *.h *.log simv* *fsdb* ucli.key verdiLog cov.vdb urgReport
