
import tkinter as tk
from tkinter import messagebox
import random
import time
import requests
import io
from PIL import Image, ImageTk

# --- 게임 설정 ---
BOARD_SIZE = 100
GRID_DIM = 10

# --- GUI 설정 ---
CELL_SIZE = 60  # 50에서 60으로 증가
CANVAS_WIDTH = CANVAS_HEIGHT = GRID_DIM * CELL_SIZE
PLAYER_COLORS = ['#FF6347', '#4682B4', '#32CD32', '#FFD700']

# --- 게임 설정 변수 (초기 설정 화면에서 변경 가능) ---
NUM_SNAKES = 10
NUM_LADDERS = 10
NUM_PLAYERS = 2  # 2, 3, 4 중 선택
NUM_COMPUTER_PLAYERS = 1  # 컴퓨터 플레이어 수

class SetupDialog:
    """게임 시작 전 초기 설정을 위한 다이얼로그"""
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("게임 설정")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.result = None
        
        # 플레이어 수 설정
        player_frame = tk.LabelFrame(self.dialog, text="플레이어 설정", padx=10, pady=10)
        player_frame.pack(padx=20, pady=10, fill="both")
        
        tk.Label(player_frame, text="총 플레이어 수:").grid(row=0, column=0, sticky="w", pady=5)
        self.total_players_var = tk.IntVar(value=2)
        total_players_spinbox = tk.Spinbox(player_frame, from_=2, to=4, textvariable=self.total_players_var, 
                                          width=10, command=self.validate_players)
        total_players_spinbox.grid(row=0, column=1, pady=5)
        
        tk.Label(player_frame, text="컴퓨터 플레이어 수:").grid(row=1, column=0, sticky="w", pady=5)
        self.computer_players_var = tk.IntVar(value=1)
        self.computer_players_spinbox = tk.Spinbox(player_frame, from_=0, to=3, 
                                                   textvariable=self.computer_players_var, 
                                                   width=10, command=self.validate_players)
        self.computer_players_spinbox.grid(row=1, column=1, pady=5)
        
        # 뱀과 사다리 설정
        elements_frame = tk.LabelFrame(self.dialog, text="뱀과 사다리 설정", padx=10, pady=10)
        elements_frame.pack(padx=20, pady=10, fill="both")
        
        tk.Label(elements_frame, text="사다리 개수:").grid(row=0, column=0, sticky="w", pady=5)
        self.ladders_var = tk.IntVar(value=10)
        tk.Spinbox(elements_frame, from_=5, to=20, textvariable=self.ladders_var, width=10).grid(row=0, column=1, pady=5)
        
        tk.Label(elements_frame, text="뱀 개수:").grid(row=1, column=0, sticky="w", pady=5)
        self.snakes_var = tk.IntVar(value=10)
        tk.Spinbox(elements_frame, from_=5, to=20, textvariable=self.snakes_var, width=10).grid(row=1, column=1, pady=5)
        
        # 경고 레이블
        self.warning_label = tk.Label(self.dialog, text="", fg="red")
        self.warning_label.pack(pady=5)
        
        # 버튼
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="시작", command=self.ok_clicked, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="취소", command=self.cancel_clicked, width=10).pack(side=tk.LEFT, padx=5)
        
        # 초기 검증
        self.validate_players()
        
        # 다이얼로그 중앙 정렬
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def validate_players(self):
        """플레이어 수 검증"""
        total = self.total_players_var.get()
        computer = self.computer_players_var.get()
        
        if computer >= total:
            self.warning_label.config(text="컴퓨터 플레이어 수는 총 플레이어 수보다 작아야 합니다.")
            return False
        else:
            self.warning_label.config(text="")
            return True
    
    def ok_clicked(self):
        """시작 버튼 클릭"""
        if not self.validate_players():
            return
        
        self.result = {
            'total_players': self.total_players_var.get(),
            'computer_players': self.computer_players_var.get(),
            'ladders': self.ladders_var.get(),
            'snakes': self.snakes_var.get()
        }
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """취소 버튼 클릭"""
        self.result = None
        self.dialog.destroy()

class SnakeAndLadderGame:
    def __init__(self, root):
        self.root = root
        self.root.title("뱀 사다리 게임")
        self.root.resizable(True, True)  # 창 크기 조절 가능하도록 변경

        self.player_images = [] # 포켓몬 이미지를 저장할 리스트
        
        # 게임 설정 변수
        self.num_players = NUM_PLAYERS
        self.num_computer_players = NUM_COMPUTER_PLAYERS
        self.num_snakes = NUM_SNAKES
        self.num_ladders = NUM_LADDERS
        # 컴퓨터 플레이어는 마지막 인덱스부터 시작 (예: 4명 중 2명이 컴퓨터면 인덱스 2, 3)
        self.computer_player_start_index = NUM_PLAYERS - NUM_COMPUTER_PLAYERS

        self.canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='white')
        self.canvas.pack(pady=10, padx=10)

        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)

        self.dice_label = tk.Label(control_frame, text="주사위: -", font=('Helvetica', 14))
        self.dice_label.pack(side=tk.LEFT, padx=10)

        self.roll_button = tk.Button(control_frame, text="주사위 굴리기", font=('Helvetica', 14), command=self.play_turn)
        self.roll_button.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(root, text="", font=('Helvetica', 14), fg='blue')
        self.status_label.pack(pady=10)

        # 초기 설정 화면 표시
        self.show_setup_dialog()

    def show_setup_dialog(self):
        """초기 설정 다이얼로그 표시"""
        setup = SetupDialog(self.root)
        self.root.wait_window(setup.dialog)
        
        if setup.result:
            # 설정 적용
            self.num_players = setup.result['total_players']
            self.num_computer_players = setup.result['computer_players']
            self.num_snakes = setup.result['snakes']
            self.num_ladders = setup.result['ladders']
            # 컴퓨터 플레이어는 마지막 인덱스부터 시작
            self.computer_player_start_index = self.num_players - self.num_computer_players
            
            self.start_new_game()
        else:
            # 취소 시 기본값으로 게임 시작
            self.start_new_game()

    def is_computer_player(self, player_index):
        """주어진 플레이어 인덱스가 컴퓨터 플레이어인지 확인"""
        return player_index >= self.computer_player_start_index

    def get_player_name(self, player_index):
        """플레이어 인덱스에 대한 이름 반환"""
        if self.is_computer_player(player_index):
            computer_number = player_index - self.computer_player_start_index + 1
            return f"컴퓨터 {computer_number}" if self.num_computer_players > 1 else "컴퓨터"
        else:
            return f"플레이어 {player_index + 1}"

    def start_new_game(self):
        """새 게임을 시작하고 모든 변수를 초기화합니다."""
        self.snakes = {}
        self.ladders = {}
        self.player_positions = [1] * self.num_players
        self.current_player = 0
        self.game_over = False
        
        self.load_player_sprites() # 포켓몬 이미지 로드
        self.setup_board_elements()
        self.draw_board()
        self.update_status()
        self.roll_button.config(state=tk.NORMAL, text="주사위 굴리기", command=self.play_turn)

    def setup_board_elements(self):
        """뱀과 사다리를 랜덤하게 생성합니다."""
        occupied_squares = {1, BOARD_SIZE}
        self.snakes.clear()
        self.ladders.clear()

        # 사다리 생성
        attempts = 0
        while len(self.ladders) < self.num_ladders and attempts < 1000:
            start = random.randint(2, BOARD_SIZE - GRID_DIM)
            
            end_min = start + 1 # 최소한 한 칸은 위로
            end_max = min(start + 20, BOARD_SIZE - 1)

            if end_min >= end_max:
                attempts += 1
                continue

            end = random.randint(end_min, end_max)

            if start not in occupied_squares and end not in occupied_squares and start // GRID_DIM < end // GRID_DIM:
                self.ladders[start] = end
                occupied_squares.add(start)
                occupied_squares.add(end)
            attempts += 1

        # 뱀 생성
        attempts = 0
        while len(self.snakes) < self.num_snakes and attempts < 1000:
            start = random.randint(GRID_DIM + 1, BOARD_SIZE - 1)

            end_max = start - 1 # 최소한 한 칸은 아래로
            end_min = max(2, start - 20)
            
            if end_min >= end_max:
                attempts += 1
                continue

            end = random.randint(end_min, end_max)

            if start not in occupied_squares and end not in occupied_squares and start // GRID_DIM > end // GRID_DIM:
                self.snakes[start] = end
                occupied_squares.add(start)
                occupied_squares.add(end)
            attempts += 1

    def get_coords(self, square):
        """칸 번호를 Canvas 좌표로 변환합니다."""
        square -= 1
        row = square // GRID_DIM
        col = square % GRID_DIM
        
        if row % 2 != 0:  # 홀수 줄 (1, 3, 5...)은 오른쪽에서 왼쪽으로
            col = GRID_DIM - 1 - col
            
        x = col * CELL_SIZE
        y = CANVAS_HEIGHT - (row + 1) * CELL_SIZE
        return x + CELL_SIZE / 2, y + CELL_SIZE / 2

    def draw_board(self):
        """보드, 칸 번호, 뱀과 사다리를 그립니다."""
        self.canvas.delete("all")
        for i in range(GRID_DIM):
            for j in range(GRID_DIM):
                x1, y1 = j * CELL_SIZE, i * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                fill_color = "#F0E68C" if (i + j) % 2 == 0 else "#FFFACD"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="black")
                
                square_num = (GRID_DIM - i - 1) * GRID_DIM
                if (GRID_DIM - i - 1) % 2 == 0:
                    square_num += j + 1
                else:
                    square_num += GRID_DIM - j
                
                self.canvas.create_text(x1 + CELL_SIZE/2, y1 + CELL_SIZE/2, text=str(square_num), font=('Helvetica', 10))

        # 사다리 그리기 (파란색, 더 굵고 화살표 크게)
        for start, end in self.ladders.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='#0066CC', width=6, arrow=tk.LAST, 
                                  arrowshape=(16, 20, 6), smooth=True)

        # 뱀 그리기 (빨간색, 더 굵고 화살표 크게)
        for start, end in self.snakes.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='#CC0000', width=6, arrow=tk.LAST, 
                                  arrowshape=(16, 20, 6), smooth=True)
            
        self.draw_players()

    def load_player_sprites(self):
        """PokeAPI에서 플레이어 수만큼 랜덤 포켓몬 이미지를 불러옵니다."""
        self.player_images = []
        self.status_label.config(text="포켓몬을 불러오는 중...")
        self.root.update_idletasks()
        
        try:
            # 전체 포켓몬 수 확인
            response = requests.get("https://pokeapi.co/api/v2/pokemon-species/?limit=1", timeout=5)
            response.raise_for_status()
            count = response.json()['count']

            for i in range(self.num_players):
                random_id = random.randint(1, count)
                poke_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{random_id}", timeout=5)
                poke_response.raise_for_status()
                sprite_url = poke_response.json()['sprites']['front_default']
                
                if not sprite_url:
                    raise ValueError("Sprite URL not found")

                # 이미지 다운로드 및 리사이즈
                img_data = requests.get(sprite_url, timeout=5).content
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((35, 35), Image.Resampling.LANCZOS)
                
                self.player_images.append(ImageTk.PhotoImage(img))
            
            print(f"성공적으로 {self.num_players}마리의 포켓몬을 불러왔습니다.")

        except Exception as e:
            print(f"포켓몬 이미지 로딩 실패: {e}. 기본 말로 대체합니다.")
            self.player_images = [] # 실패 시 이미지 리스트 초기화

    def draw_players(self):
        """플레이어 말을 그립니다. (포켓몬 또는 기본 도형)"""
        self.canvas.delete("player")
        for i, pos in enumerate(self.player_positions):
            # 100을 넘은 플레이어는 100 위치에 그립니다
            draw_pos = min(pos, BOARD_SIZE)
            x, y = self.get_coords(draw_pos)
            offset = (i - (self.num_players - 1) / 2) * 12

            if self.player_images and len(self.player_images) == self.num_players:
                self.canvas.create_image(x + offset, y, image=self.player_images[i], tags="player")
            else:
                self.canvas.create_oval(x - 10 + offset, y - 10, x + 10 + offset, y + 10, 
                                        fill=PLAYER_COLORS[i], outline='black', tags="player")

    def play_turn(self):
        """'주사위 굴리기' 버튼 클릭 시 호출되는 함수."""
        if self.game_over or self.is_computer_player(self.current_player):
            return

        self.roll_and_move()

        if not self.game_over and self.is_computer_player(self.current_player):
            self.roll_button.config(state=tk.DISABLED)
            self.root.after(1000, self.computer_turn) # 1초 후 컴퓨터 턴 실행

    def computer_turn(self):
        """컴퓨터의 턴을 자동으로 진행합니다."""
        if self.game_over:
            return
        
        self.roll_and_move()
        self.roll_button.config(state=tk.NORMAL)

    def roll_and_move(self):
        """주사위를 굴리고 말을 이동시킵니다."""
        roll = random.randint(1, 6)
        player_name = self.get_player_name(self.current_player)
        
        self.dice_label.config(text=f"주사위: {roll}")
        
        old_pos = self.player_positions[self.current_player]
        new_pos = old_pos + roll

        # 100 이상이면 그대로 이동 (승리 조건)
        self.player_positions[self.current_player] = new_pos
        self.draw_players()
        self.root.update_idletasks()
        time.sleep(0.5) # 이동 애니메이션을 위한 짧은 딜레이

        # 뱀 또는 사다리 확인 (100 이하일 때만)
        landed_on = ""
        if new_pos >= BOARD_SIZE:
            final_pos = new_pos  # 100 이상이면 승리
        elif new_pos in self.ladders:
            final_pos = self.ladders[new_pos]
            landed_on = f"사다리 발견! {new_pos} -> {final_pos}"
        elif new_pos in self.snakes:
            final_pos = self.snakes[new_pos]
            landed_on = f"뱀 발견! {new_pos} -> {final_pos}"
        else:
            final_pos = new_pos

        self.player_positions[self.current_player] = final_pos
        self.status_label.config(text=f"{player_name}이(가) {roll}을(를) 굴려 {final_pos}에 도착. {landed_on}")
        
        self.draw_players()

        if final_pos >= BOARD_SIZE:
            self.game_over = True
            messagebox.showinfo("게임 종료", f"{player_name}의 승리!")
            self.roll_button.config(text="새 게임 시작", command=self.show_setup_dialog)
        else:
            self.current_player = (self.current_player + 1) % self.num_players
            self.update_status()

    def update_status(self):
        """현재 턴 상태를 업데이트합니다."""
        if not self.game_over:
            player_name = self.get_player_name(self.current_player)
            self.status_label.config(text=f"{player_name}의 턴입니다.")

if __name__ == "__main__":
    main_root = tk.Tk()
    game = SnakeAndLadderGame(main_root)
    main_root.mainloop()
