import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk  
import socket
import random
import threading
import os
import json

# --- CONFIGURATIONS GLOBALES ---
PORT = 27535
IMAGE_SIZE = (100, 100)  

# Ajoute ici les ID des Pokémon
BLACKLIST = [144, "0144-f1", 145, "0145-f1", 146, "0146-f1", 150, 151, 243, 244, 245, 249, 250, 251, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489,
490, 491, 492, 493, 494, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 666, "0666-f01", "0666-f02", "0666-f03", "0666-f04", "0666-f05", "0666-f07", "0666-f08", "0666-f09", "0666-f10", 
"0666-f11", "0666-f12", "0666-f13", "0666-f14", "0666-f15", "0666-f16", "0666-f17", "0666-f19", "0670-f5", "0710-f1", "0710-f2", "0710-f3", "0711-f1", "0711-f2", "0711-f3", 716, 717, 718, "0718-f1", 
719, 720, 721, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, "0854-f1", "0855-f1", 888, 889, 890, 891, 892, "0892-f1", 894,
895, 896, 897, "0901-f1", 905, 999, "0999-f1", 1000, 1001, 1002, 1003, 1004, 1007, 1008, 1009, 1010, "1012-f1", "1013-f1", 1014, 1015, 1016, 1017, 1020, 1021, 1022, 1023, 1024, 
1025] # Pokémon interdits dans la grille

WHITELIST = [] # Pokémon obligatoires dans la grille
# -------------------------------

class PokemonBingoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bingo Pokémon Shiny Multi")
        self.root.configure(bg="#222222")
        
        # Variables réseau
        self.network_socket = None
        self.is_host = False
        self.connected_clients = []
        
        # Infos joueur local
        self.my_name = "Joueur"
        self.my_color = "#0077ff"
        
        # État du jeu partagé
        self.grid_data = []        # Liste de dictionnaires : [{"id": "0025", "name": "Pikachu"}, ...]
        self.players_info = {}     
        self.buttons = []          
        self.photo_images = []     
        
        self.create_menu_interface()

    def create_menu_interface(self):
        self.menu_frame = tk.Frame(self.root, bg="#222222", padx=50, pady=50)
        self.menu_frame.pack()
        
        title = tk.Label(self.menu_frame, text="BINGO POKÉMON SHINY", font=("Arial", 20, "bold"), fg="white", bg="#222222")
        title.pack(pady=20)
        
        btn_host = tk.Button(self.menu_frame, text="Héberger une partie (Joueur 1)", font=("Arial", 12), width=25, bg="#444444", fg="white", command=self.setup_host)
        btn_host.pack(pady=10)
        
        btn_join = tk.Button(self.menu_frame, text="Rejoindre une partie", font=("Arial", 12), width=25, bg="#444444", fg="white", command=self.setup_client)
        btn_join.pack(pady=10)

    def generate_filtered_grid(self):
        """Scanne tous les fichiers JSON, associe les noms et génère la grille."""
        pokemon_dict = {} # Stocke la correspondance { "id_str": "Nom du Pokemon" }
        
        json_files = ["formes.json"] + [f"gen{i}.json" for i in range(1, 10)]
        
        for file_name in json_files:
            if os.path.exists(file_name):
                try:
                    with open(file_name, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for obj in data:
                            if "id" in obj and "name" in obj:
                                raw_id = obj["id"]
                                if isinstance(raw_id, int):
                                    str_id = f"{raw_id:04d}"
                                else:
                                    str_id = str(raw_id).strip()
                                
                                pokemon_dict[str_id] = obj["name"]
                except Exception as e:
                    print(f"Erreur lors de la lecture de {file_name} : {e}")

        if not pokemon_dict:
            messagebox.showerror("Erreur", "Aucun fichier JSON valide trouvé !")
            return [{"id": f"{i:04d}", "name": f"Pokémon {i}"} for i in range(1, 26)]

        # Outil de formatage pour la BLACKLIST et WHITELIST globale
        def format_filter_item(x):
            if isinstance(x, int): return f"{x:04d}"
            if str(x).isdigit(): return f"{int(x):04d}"
            return str(x).strip()

        blacklist_set = set(format_filter_item(x) for x in BLACKLIST)
        whitelist_set = set(format_filter_item(x) for x in WHITELIST)

        # Extraction de tous les ID disponibles (le pool)
        pool_ids = set(pokemon_dict.keys()) - blacklist_set
        whitelist_set = whitelist_set - blacklist_set

        # Filtrage de la whitelist pour ne garder que ce qui existe dans le pool
        valid_whitelist = [x for x in whitelist_set if x in pool_ids]
        chosen_ids = list(valid_whitelist)

        # Complétion de la liste pour atteindre 25 Pokémon
        if len(chosen_ids) > 25:
            chosen_ids = random.sample(chosen_ids, 25)
        else:
            remaining_slots = 25 - len(chosen_ids)
            available_pool = list(pool_ids - set(chosen_ids))
            
            if len(available_pool) >= remaining_slots:
                chosen_ids += random.sample(available_pool, remaining_slots)
            else:
                chosen_ids += available_pool

        random.shuffle(chosen_ids)
        
        # On construit la structure finale de la grille : une liste d'objets avec ID et Nom
        final_grid = []
        for poke_id in chosen_ids:
            if "0710-f1" in BLACKLIST or "0711-f1" in BLACKLIST or "0854-f1" in BLACKLIST or "0855-f1" in BLACKLIST or "1012-f1" in BLACKLIST or "1013-f1" in BLACKLIST:
                if poke_id in ["0710", "0711", "0854", "0855", "1012", "1013"]:
                    poke_name = pokemon_dict[poke_id].split(" ")[0]
                    final_grid.append({"id": poke_id, "name": poke_name})
                    continue
            final_grid.append({"id": poke_id, "name": pokemon_dict[poke_id]})
        return final_grid
    
    def reset_grid_interface(self):
        """Vide l'ancienne grille graphique et reconstruit les 25 nouveaux boutons."""
        # On détruit proprement les anciens boutons de la grille
        for btn in self.buttons:
            btn.destroy()
        
        # On vide nos listes de stockage
        self.buttons.clear()
        self.photo_images.clear()
        
        # On demande à Tkinter de redessiner les nouveaux Pokémon
        for i, poke_info in enumerate(self.grid_data):
            row = i // 5
            col = i % 5
            poke_id = poke_info["id"]
            poke_name = poke_info["name"]
            
            img_path = f"images/{poke_id}.png"
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
                pil_img = pil_img.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
                img = ImageTk.PhotoImage(pil_img)
            else:
                img = ImageTk.PhotoImage(Image.new("RGBA", IMAGE_SIZE, (0,0,0,0)))
            
            self.photo_images.append(img)
            
            btn = tk.Button(
                self.game_frame, image=img, text=poke_name, compound="top",
                font=("Arial", 8, "bold"), bg="#444444", fg="white", 
                width=120, height=150, wraplength=100, justify="center",
                command=lambda idx=i: self.on_cell_left_click(idx)
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            btn.bind("<Button-3>", lambda event, idx=i: self.on_cell_right_click(idx))
            btn.bind("<Button-2>", lambda event, idx=i: self.on_cell_right_click(idx))
            self.buttons.append(btn)

    def trigger_reroll(self):
        """Action du bouton Reroll (Hôte uniquement)."""
        # 1. L'hôte génère une nouvelle grille
        self.grid_data = self.generate_filtered_grid()
        # 2. Il met à jour sa propre interface
        self.reset_grid_interface()
        # 3. Il ordonne aux clients de faire de même
        self.broadcast_message({"type": "NEW_GRID", "grid": self.grid_data})

    def get_user_profile(self):
        name = simpledialog.askstring("Profil", "Entrez votre pseudo :", initialvalue=self.my_name)
        if not name: return False
        self.my_name = name
        
        messagebox.showinfo("Couleur", "Choisissez votre couleur de Bingo !")
        _, hex_color = colorchooser.askcolor(title="Choisissez votre couleur")
        if hex_color:
            self.my_color = hex_color
        return True

    def setup_host(self):
        if not self.get_user_profile(): return
        self.is_host = True
        
        self.grid_data = self.generate_filtered_grid()
        self.players_info[self.my_name] = self.my_color
        
        threading.Thread(target=self.host_server_thread, daemon=True).start()
        self.start_game_interface()

    def host_server_thread(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind(('0.0.0.0', PORT))
            server_socket.listen(4)
            
            while True:
                client_sock, addr = server_socket.accept()
                self.connected_clients.append(client_sock)
                threading.Thread(target=self.handle_client_messages, args=(client_sock,), daemon=True).start()
        except Exception as e:
            print(f"Erreur serveur : {e}")

    def handle_client_messages(self, client_sock):
        while True:
            try:
                data = client_sock.recv(4096).decode()
                if not data: break
                
                msg = json.loads(data)
                
                if msg["type"] == "JOIN":
                    self.players_info[msg["name"]] = msg["color"]
                    self.root.after(0, self.update_legend)
                    
                    response = {
                        "type": "INIT_DATA",
                        "grid": self.grid_data, # Contient désormais les ID ET les Noms
                        "players": self.players_info
                    }
                    client_sock.send(json.dumps(response).encode())
                    self.broadcast_message({"type": "NEW_PLAYER", "name": msg["name"], "color": msg["color"]})
                
                elif msg["type"] in ["CLICK", "UNCLICK"]:
                    self.root.after(0, self.update_cell_color, msg["index"], msg["color"])
                    self.broadcast_message(msg)
                
                elif msg["type"] == "REROLL":
                    # L'hôte régénère la grille localement
                    self.grid_data = self.generate_filtered_grid()
                    # Il remet à zéro l'interface chez lui
                    self.root.after(0, self.reset_grid_interface)
                    # Il envoie la nouvelle grille à TOUT LE MONDE
                    self.broadcast_message({"type": "NEW_GRID", "grid": self.grid_data})
                    
            except:
                break
        
        if client_sock in self.connected_clients:
            self.connected_clients.remove(client_sock)

    def broadcast_message(self, message_dict):
        encoded_msg = json.dumps(message_dict).encode()
        for client in self.connected_clients:
            try:
                client.send(encoded_msg)
            except:
                pass

    def setup_client(self):
        target_ip = simpledialog.askstring("Connexion", "Adresse IP de l'hôte :", initialvalue="127.0.0.1")
        if not target_ip: return
        if not self.get_user_profile(): return
        
        try:
            self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.network_socket.connect((target_ip, PORT))
            
            join_msg = {"type": "JOIN", "name": self.my_name, "color": self.my_color}
            self.network_socket.send(json.dumps(join_msg).encode())
            
            data = self.network_socket.recv(4096).decode()
            msg = json.loads(data)
            
            if msg["type"] == "INIT_DATA":
                self.grid_data = msg["grid"]
                self.players_info = msg["players"]
                self.start_game_interface()
                threading.Thread(target=self.listen_to_host, daemon=True).start()
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Connexion impossible à {target_ip}\n{e}")

    def listen_to_host(self):
        while True:
            try:
                data = self.network_socket.recv(4096).decode()
                if not data: break
                msg = json.loads(data)
                
                if msg["type"] == "NEW_PLAYER":
                    self.players_info[msg["name"]] = msg["color"]
                    self.root.after(0, self.update_legend)
                    
                elif msg["type"] in ["CLICK", "UNCLICK"]:
                    self.root.after(0, self.update_cell_color, msg["index"], msg["color"])
                
                elif msg["type"] == "NEW_GRID":
                    self.grid_data = msg["grid"]
                    # Le client efface ses grilles et recharge la nouvelle
                    self.root.after(0, self.reset_grid_interface)
            except:
                break

    def start_game_interface(self):
        self.menu_frame.pack_forget()
        
        self.main_container = tk.Frame(self.root, bg="#222222", padx=10, pady=10)
        self.main_container.pack()
        
        self.game_frame = tk.Frame(self.main_container, bg="#333333", padx=5, pady=5)
        self.game_frame.pack(side=tk.LEFT, padx=10)
        
        self.legend_frame = tk.Frame(self.main_container, bg="#2b2b2b", padx=15, pady=15, bd=2, relief=tk.RIDGE)
        self.legend_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        lbl_title_leg = tk.Label(self.legend_frame, text="JOUEURS", font=("Arial", 12, "bold"), fg="white", bg="#2b2b2b")
        lbl_title_leg.pack(pady=(0, 10))
        
        self.update_legend()

        for i, poke_info in enumerate(self.grid_data):
            row = i // 5
            col = i % 5
            
            poke_id = poke_info["id"]
            poke_name = poke_info["name"]
            
            img_path = f"images/{poke_id}.png"
            
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
                pil_img = pil_img.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
                img = ImageTk.PhotoImage(pil_img)
            else:
                img = ImageTk.PhotoImage(Image.new("RGBA", IMAGE_SIZE, (0,0,0,0)))
            
            self.photo_images.append(img)
            
            # --- MODIFICATION DE L'AFFICHAGE ---
            # Le bouton affiche désormais le vrai nom du Pokémon (ex: "Rattata Forme d'Alola")
            # Le bouton s'agrandit légèrement en largeur (width=110) pour laisser de la place aux longs noms
            btn = tk.Button(
                self.game_frame, 
                image=img, 
                text=poke_name, 
                compound="top",
                font=("Arial", 8, "bold"),
                bg="#444444", 
                fg="white", 
                width=120, 
                height=150,
                wraplength=100, # Aligne le texte sur plusieurs lignes proprement s'il est trop long
                justify="center",
                command=lambda idx=i: self.on_cell_left_click(idx)
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            
            btn.bind("<Button-3>", lambda event, idx=i: self.on_cell_right_click(idx))
            btn.bind("<Button-2>", lambda event, idx=i: self.on_cell_right_click(idx))
            
            self.buttons.append(btn)
        
        # --- BOUTON REROLL POUR L'HÔTE ---
        if self.is_host:
            btn_reroll = tk.Button(
                self.legend_frame, # On le place en bas de la légende à droite
                text="🔄 REROLL LA GRILLE",
                font=("Arial", 10, "bold"),
                bg="#ff9900",
                fg="black",
                command=self.trigger_reroll
            )
            btn_reroll.pack(pady=20, fill=tk.X)

    def update_legend(self):
        for widget in self.legend_frame.winfo_children():
            if widget.cget("text") != "JOUEURS":
                widget.destroy()
                
        for name, color in self.players_info.items():
            tk.Label(self.legend_frame, text=name, font=("Arial", 11, "bold"), fg=color, bg="#2b2b2b", pady=4).pack(anchor="w")

    def on_cell_left_click(self, index):
        btn = self.buttons[index]
        if btn.cget("bg") != "#444444": return 
            
        self.update_cell_color(index, self.my_color)
        self.send_network_event({"type": "CLICK", "index": index, "color": self.my_color})

    def on_cell_right_click(self, index):
        btn = self.buttons[index]
        if btn.cget("bg") == "#444444": return 
        
        self.update_cell_color(index, "#444444") 
        self.send_network_event({"type": "UNCLICK", "index": index, "color": "#444444"})

    def send_network_event(self, msg_dict):
        try:
            if self.is_host:
                self.broadcast_message(msg_dict)
            elif self.network_socket:
                self.network_socket.send(json.dumps(msg_dict).encode())
        except Exception as e:
            print(f"Erreur d'envoi réseau : {e}")

    def update_cell_color(self, index, color):
        if 0 <= index < len(self.buttons):
            self.buttons[index].config(bg=color, activebackground=color)

if __name__ == "__main__":
    root = tk.Tk()
    app = PokemonBingoApp(root)
    root.mainloop()