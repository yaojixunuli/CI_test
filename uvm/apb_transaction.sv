class apb_transaction extends uvm_sequence_item;

   rand bit          write;
   rand bit[31:0]    addr;
   rand bit[31:0]    data;

   constraint addr_range { addr[31:6] == 26'b0; addr[1:0] == 2'b00; }

   `uvm_object_utils_begin(apb_transaction)
      `uvm_field_int(addr, UVM_ALL_ON)
      `uvm_field_int(data, UVM_ALL_ON)
      `uvm_field_int(write, UVM_ALL_ON)
   `uvm_object_utils_end

   function new(string name = "apb_transaction");
      super.new(name);
   endfunction

endclass
