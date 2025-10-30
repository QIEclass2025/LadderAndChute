
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
NUM_SNAKES = 10
NUM_LADDERS = 10
NUM_PLAYERS = 2  # 2, 3, 4 중 선택 (마지막 플레이어는 항상 컴퓨터)

# --- GUI 설정 ---
CELL_SIZE = 50
CANVAS_WIDTH = CANVAS_HEIGHT = GRID_DIM * CELL_SIZE
PLAYER_COLORS = ['#FF6347', '#4682B4', '#32CD32', '#FFD700']
COMPUTER_PLAYER_INDEX = NUM_PLAYERS - 1

class SnakeAndLadderGame:
    def __init__(self, root):
        self.root = root
        self.root.title("뱀 사다리 게임")
        self.root.resizable(False, False)

        self.player_images = [] # 포켓몬 이미지를 저장할 리스트

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

        self.start_new_game()

    def start_new_game(self):
        """새 게임을 시작하고 모든 변수를 초기화합니다."""
        self.snakes = {}
        self.ladders = {}
        self.player_positions = [1] * NUM_PLAYERS
        self.current_player = 0
        self.game_over = False
        
        self.load_player_sprites() # 포켓몬 이미지 로드
        self.setup_board_elements()
        self.draw_board()
        self.update_status()
        self.roll_button.config(state=tk.NORMAL)

    def setup_board_elements(self):
        """뱀과 사다리를 랜덤하게 생성합니다."""
        occupied_squares = {1, BOARD_SIZE}
        self.snakes.clear()
        self.ladders.clear()

        # 사다리 생성
        attempts = 0
        while len(self.ladders) < NUM_LADDERS and attempts < 1000:
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
        while len(self.snakes) < NUM_SNAKES and attempts < 1000:
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

        # 사다리 그리기 (파란색)
        for start, end in self.ladders.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='blue', width=4, arrow=tk.LAST)

        # 뱀 그리기 (빨간색)
        for start, end in self.snakes.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='red', width=4, arrow=tk.LAST)
            
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

            for i in range(NUM_PLAYERS):
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
            
            print(f"성공적으로 {NUM_PLAYERS}마리의 포켓몬을 불러왔습니다.")

        except Exception as e:
            print(f"포켓몬 이미지 로딩 실패: {e}. 기본 말로 대체합니다.")
            self.player_images = [] # 실패 시 이미지 리스트 초기화

    def draw_players(self):
        """플레이어 말을 그립니다. (포켓몬 또는 기본 도형)"""
        self.canvas.delete("player")
        for i, pos in enumerate(self.player_positions):
            x, y = self.get_coords(pos)
            offset = (i - (NUM_PLAYERS - 1) / 2) * 12

            if self.player_images and len(self.player_images) == NUM_PLAYERS:
                self.canvas.create_image(x + offset, y, image=self.player_images[i], tags="player")
            else:
                self.canvas.create_oval(x - 10 + offset, y - 10, x + 10 + offset, y + 10, 
                                        fill=PLAYER_COLORS[i], outline='black', tags="player")

    def play_turn(self):
        """'주사위 굴리기' 버튼 클릭 시 호출되는 함수."""
        if self.game_over or self.current_player == COMPUTER_PLAYER_INDEX:
            return

        self.roll_and_move()

        if not self.game_over and self.current_player == COMPUTER_PLAYER_INDEX:
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
        player_name = f"플레이어 {self.current_player + 1}"
        if self.current_player == COMPUTER_PLAYER_INDEX:
            player_name = "컴퓨터"
        
        self.dice_label.config(text=f"주사위: {roll}")
        
        old_pos = self.player_positions[self.current_player]
        new_pos = old_pos + roll

        if new_pos > BOARD_SIZE:
            new_pos = old_pos # 100을 넘어가면 이동하지 않음
        
        self.player_positions[self.current_player] = new_pos
        self.draw_players()
        self.root.update_idletasks()
        time.sleep(0.5) # 이동 애니메이션을 위한 짧은 딜레이

        # 뱀 또는 사다리 확인
        landed_on = ""
        if new_pos in self.ladders:
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

        if final_pos == BOARD_SIZE:
            self.game_over = True
            messagebox.showinfo("게임 종료", f"{player_name}의 승리!")
            self.roll_button.config(text="새 게임 시작", command=self.start_new_game)
        else:
            self.current_player = (self.current_player + 1) % NUM_PLAYERS
            self.update_status()

    def update_status(self):
        """현재 턴 상태를 업데이트합니다."""
        if not self.game_over:
            player_name = f"플레이어 {self.current_player + 1}"
            if self.current_player == COMPUTER_PLAYER_INDEX:
                player_name = "컴퓨터"
            self.status_label.config(text=f"{player_name}의 턴입니다.")

if __name__ == "__main__":
    main_root = tk.Tk()
    game = SnakeAndLadderGame(main_root)
    main_root.mainloop()
