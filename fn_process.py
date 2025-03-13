import ctypes
import struct
import psutil
import sys
import os

# Carrega a biblioteca libSystem.dylib (contém as APIs do macOS)
libc = ctypes.CDLL("/usr/lib/libSystem.dylib")

# Define tipos e constantes
kern_return_t = ctypes.c_int
task_t = ctypes.c_uint
mach_vm_address_t = ctypes.c_uint64
mach_vm_size_t = ctypes.c_uint64
vm_offset_t = ctypes.POINTER(ctypes.c_uint32)
mach_msg_type_number_t = ctypes.POINTER(ctypes.c_uint32)

# Protótipos das funções
libc.task_for_pid.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(task_t)]
libc.task_for_pid.restype = kern_return_t

libc.mach_vm_read.argtypes = [task_t, mach_vm_address_t, mach_vm_size_t, ctypes.POINTER(vm_offset_t), ctypes.POINTER(mach_msg_type_number_t)]
libc.mach_vm_read.restype = kern_return_t

libc.mach_vm_write.argtypes = [task_t, mach_vm_address_t, ctypes.c_void_p, mach_vm_size_t]
libc.mach_vm_write.restype = kern_return_t

libc.mach_task_self.argtypes = []
libc.mach_task_self.restype = ctypes.c_int

def check_permissions():
    if os.geteuid() != 0:
        print("[ERRO] Este programa requer permissões de administrador! Rode com: sudo python3 mdeus.py")
        sys.exit(1)

def get_pid(process_name):
    for proc in psutil.process_iter():
        if proc.name().lower() == process_name.lower():
            return proc.pid
    return None

def read_process_memory(pid, address, size):
    task = task_t()
    ret = libc.task_for_pid(libc.mach_task_self(), pid, ctypes.byref(task))
    if ret != 0:
        print(f"[ERRO] task_for_pid falhou ({ret}). Tente rodar com sudo.")
        return None
    
    data = vm_offset_t()
    data_count = mach_msg_type_number_t()
    ret = libc.mach_vm_read(task, address, size, ctypes.byref(data), ctypes.byref(data_count))
    if ret != 0:
        print(f"[ERRO] Falha ao ler memória ({ret}).")
        return None
    
    buffer = ctypes.create_string_buffer(size)
    ctypes.memmove(buffer, data, size)
    return buffer.raw

def write_process_memory(pid, address, new_value):
    task = task_t()
    ret = libc.task_for_pid(libc.mach_task_self(), pid, ctypes.byref(task))
    if ret != 0:
        print(f"[ERRO] task_for_pid falhou ({ret}). Tente rodar com sudo.")
        return False
    
    try:
        # REMOVA ESTA LINHA: address_int = int(address, 16)
        new_bytes = bytes.fromhex(new_value.replace(" ", ""))
        size = len(new_bytes)
        buffer = ctypes.create_string_buffer(new_bytes)
        ret = libc.mach_vm_write(task, ctypes.c_uint64(address), ctypes.cast(buffer, ctypes.c_void_p), size)
        if ret != 0:
            print(f"[ERRO] Falha ao escrever memória em {hex(address)} ({ret}).")
            return False
        return True
    except Exception as e:
        print(f"[ERRO] Exceção ao escrever memória: {e}")
        return False

def find_memory_address(pid, value, search_mode, scan_size=0x100000):
    print(f"Buscando ({search_mode})...")
    sys.stdout.flush()
    
    task = task_t()
    ret = libc.task_for_pid(libc.mach_task_self(), pid, ctypes.byref(task))
    if ret != 0:
        return []

    start_address = 0x000000000
    end_address = 0x11660D8CC
    
    if search_mode == "AOB":
        search_bytes = bytes.fromhex(value.replace(" ", ""))
    elif search_mode == "1B":
        search_bytes = bytes.fromhex(value.zfill(2))  # 1 byte
    elif search_mode == "4B":
        search_bytes = bytes.fromhex(value.zfill(8))  # 4 bytes
    else:
        print("[ERRO] Modo de busca inválido.")
        return []
    step = 1 if len(search_bytes) < 4 else len(search_bytes)
    found_addresses = set()  # Usando set() para remover duplicatas
    
    for address in range(start_address, end_address, step):
        memory_data = read_process_memory(pid, address, len(search_bytes))
        if memory_data and memory_data == search_bytes:
            found_addresses.add((hex(address), memory_data.hex()))
            print(f"{hex(address)} {memory_data.hex()}")
            sys.stdout.flush()
    
    return sorted(found_addresses, key=lambda x: int(x[0], 16))

def main():
    check_permissions()
    if len(sys.argv) < 4:
        print("Uso: sudo python3 fn_process.py <PID> <VALOR> <MODO>")
        return
    
    process = sys.argv[1]
    value = sys.argv[2]
    search_mode = sys.argv[3]
    
    try:
        pid = int(process)
    except ValueError:
        pid = get_pid(process)
        if pid is None:
            print("[ERRO] Processo não encontrado.")
            return
    
    addresses = find_memory_address(pid, value, search_mode)
    if addresses:
        print("Endereços encontrados:")
        for addr, val in addresses:
            print(f"{addr} {val}")
    else:
        print("Nenhum endereço encontrado.")
    
if __name__ == "__main__":
    main()
