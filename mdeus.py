import os
import tkinter as tk
from tkinter import ttk
import subprocess
import threading

import psutil
from fn_process import get_pid, write_process_memory

def refresh_process_list():
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        processes.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
    return sorted(processes)

def start_process():
    selected = process_combobox.get()
    if not selected:
        process = process_name.get().strip()
        if not process:
            status_label.config(text="Erro: processo obrigatorio.", fg="red")
        pid = get_pid(process)
        if pid:
            pid_label.config(text=f"PID encontrado: {pid}")
        else:
            pid_label.config(text="PID não encontrado", fg="red")
            return
        status_label.config(text="Selecione um processo!", fg="red")
        return
    else:
        pid = int(selected.split("PID: ")[1].replace(")", ""))
    value = value_input.get().strip()
    search_mode = search_mode_var.get()
    
    if search_mode == "AOB" and len( value.replace(" ", "")) % 2 != 0:
        status_label.config(text="Erro: Valor inválido (número ímpar de dígitos).", fg="red")
        return
    status_label.config(text="Buscando...")
    address_count_label.config(text="Endereços buscados: 0")
    address_result_frame.pack_forget()
    root.update()
    
    
    
    def run_search():
        if os.geteuid() != 0:
            status_label.config(text="Erro: Execute com sudo.", fg="red")
            return
        
        command = ["sudo", "python3", "fn_process.py", str(pid), value, search_mode]
        process_output = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        address_count = 0
        addresses_found = set()  # Usa um set() para garantir valores únicos
        
        for line in iter(process_output.stdout.readline, ""):
            line = line.strip()
            if line.startswith("0x"):  # Filtra endereços encontrados
                parts = line.split(" ")
                if len(parts) == 2:
                    addr, val = parts
                    addresses_found.add((addr, val))  # Adiciona ao set para evitar duplicação
                    address_count += 1
                    address_count_label.config(text=f"Endereços buscados: {address_count}")
                    root.update()
        
        process_output.stdout.close()
        process_output.wait()
        
        if addresses_found:
            status_label.config(text="Busca concluída.", fg="green")
            show_address_editor(pid, sorted(addresses_found, key=lambda x: int(x[0], 16)))
        else:
            status_label.config(text="Nenhum endereço encontrado.", fg="red")
    
    threading.Thread(target=run_search, daemon=True).start()

def show_address_editor(pid, addresses):
    for widget in address_result_frame.winfo_children():
        widget.destroy()
    
    tk.Label(address_result_frame, text="Editar valores (hex):").pack()
    
    for addr, val in addresses:
        frame = tk.Frame(address_result_frame)
        frame.pack(pady=2)
        tk.Label(frame, text=f"{addr}:").pack(side=tk.LEFT)
        entry = tk.Entry(frame, width=10)
        entry.insert(0, val)
        entry.pack(side=tk.LEFT)
        tk.Button(
            frame,
            text="Salvar",
            command=lambda a=addr, e=entry: update_memory(pid, a, e)
        ).pack(side=tk.LEFT)
    
    address_result_frame.pack()

def update_memory(pid, address, entry):
    new_value = entry.get().strip()
    try:
        # Verifica se o valor é hexadecimal válido
        bytes.fromhex(new_value.replace(" ", ""))
    except ValueError:
        status_label.config(text="Valor inválido. Use apenas hex (ex: 01A2B3).", fg="red")
        return
    
    if write_process_memory(pid, int(address, 16), new_value):
        status_label.config(text=f"Valor atualizado em {address}!", fg="green")
    else:
        status_label.config(text=f"Erro ao atualizar {address}.", fg="red")

# Criação da janela principal
root = tk.Tk()
root.title("Modo Deus")
root.geometry("400x650")

label_process = tk.Label(root, text="Selecione o processo:")
label_process.pack(pady=10)

global process_combobox
process_combobox = ttk.Combobox(root, width=50)
process_combobox['values'] = refresh_process_list()
process_combobox.pack(pady=5)

# Adicione botão de atualização
btn_refresh = tk.Button(root, text="↺", command=lambda: process_combobox['values'])
btn_refresh.pack()

# Rótulo para instrução
label_process = tk.Label(root, text="Nome do processo ou PID:")
label_process.pack(pady=10)

# Caixa de entrada para o nome do processo ou PID
process_name = tk.Entry(root, width=50)
process_name.pack(pady=5)

# Rótulo do PID encontrado
pid_label = tk.Label(root, text="PID: Não encontrado")
pid_label.pack(pady=5)

# Rótulo para busca de valor
label_value = tk.Label(root, text="Valor a ser buscado:")
label_value.pack(pady=10)

# Caixa de entrada para o valor a ser buscado
value_input = tk.Entry(root, width=50)
value_input.pack(pady=5)

# Opções de tipo de busca
search_mode_var = tk.StringVar(value="AOB")
search_mode_frame = tk.Frame(root)
search_mode_frame.pack(pady=5)
tk.Label(search_mode_frame, text="Tipo de busca:").pack(side=tk.LEFT)
tk.Radiobutton(search_mode_frame, text="AOB", variable=search_mode_var, value="AOB").pack(side=tk.LEFT)
tk.Radiobutton(search_mode_frame, text="1 Byte", variable=search_mode_var, value="1B").pack(side=tk.LEFT)
tk.Radiobutton(search_mode_frame, text="4 Bytes", variable=search_mode_var, value="4B").pack(side=tk.LEFT)

# Status da busca
status_label = tk.Label(root, text="")
status_label.pack(pady=5)

# Contador de endereços buscados
address_count_label = tk.Label(root, text="Endereços buscados: 0")
address_count_label.pack(pady=5)

# Frame para exibição e edição dos endereços encontrados
address_result_frame = tk.Frame(root)
address_result_frame.pack(pady=5)

# Botão para iniciar a busca
atracar = tk.Button(
    root,
    text="Atracar",
    command=start_process
)
atracar.pack(pady=5)

# Executa a janela
root.mainloop()
