
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

# --- 기본 게임 설정 (초기 설정 화면의 기본값) ---
DEFAULT_NUM_SNAKES = 10
DEFAULT_NUM_LADDERS = 10
DEFAULT_NUM_PLAYERS = 2
DEFAULT_NUM_COMPUTER_PLAYERS = 1

class SetupPanel:
    """메인 윈도우에 합쳐져서 표시되는 게임 설정 패널"""
    def __init__(self, parent, on_submit, on_cancel):
        self.parent = parent
        self.on_submit = on_submit
        self.on_cancel = on_cancel

        self.frame = tk.Frame(parent, padx=20, pady=20)
        self.frame.pack(fill="both", expand=True)

        title = tk.Label(self.frame, text="게임 설정", font=('Helvetica', 16, 'bold'))
        title.pack(pady=(0, 10))

        # 플레이어 수 설정
        player_frame = tk.LabelFrame(self.frame, text="플레이어 설정", padx=10, pady=10)
        player_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(player_frame, text="총 플레이어 수:").grid(row=0, column=0, sticky="w", pady=5)
        self.total_players_var = tk.IntVar(value=DEFAULT_NUM_PLAYERS)
        total_players_spinbox = tk.Spinbox(player_frame, from_=2, to=4, textvariable=self.total_players_var,
                                           width=10, command=self.validate_players)
        total_players_spinbox.grid(row=0, column=1, pady=5, padx=(10, 0))

        tk.Label(player_frame, text="컴퓨터 플레이어 수:").grid(row=1, column=0, sticky="w", pady=5)
        self.computer_players_var = tk.IntVar(value=DEFAULT_NUM_COMPUTER_PLAYERS)
        self.computer_players_spinbox = tk.Spinbox(player_frame, from_=0, to=3,
                                                   textvariable=self.computer_players_var,
                                                   width=10, command=self.validate_players)
        self.computer_players_spinbox.grid(row=1, column=1, pady=5, padx=(10, 0))

        # 뱀과 사다리 설정
        elements_frame = tk.LabelFrame(self.frame, text="뱀과 사다리 설정", padx=10, pady=10)
        elements_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(elements_frame, text="사다리 개수:").grid(row=0, column=0, sticky="w", pady=5)
        self.ladders_var = tk.IntVar(value=DEFAULT_NUM_LADDERS)
        tk.Spinbox(elements_frame, from_=5, to=20, textvariable=self.ladders_var, width=10).grid(row=0, column=1, pady=5, padx=(10, 0))

        tk.Label(elements_frame, text="뱀 개수:").grid(row=1, column=0, sticky="w", pady=5)
        self.snakes_var = tk.IntVar(value=DEFAULT_NUM_SNAKES)
        tk.Spinbox(elements_frame, from_=5, to=20, textvariable=self.snakes_var, width=10).grid(row=1, column=1, pady=5, padx=(10, 0))

        # 경고 레이블
        self.warning_label = tk.Label(self.frame, text="", fg="red")
        self.warning_label.pack(pady=(0, 5))

        # 버튼
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="시작", command=self.ok_clicked, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="취소", command=self.cancel_clicked, width=12).pack(side=tk.LEFT, padx=5)

        # 초기 검증
        self.validate_players()

    def destroy(self):
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None

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
        """시작 버튼 클릭 (유효하면 콜백으로 결과 전달)"""
        if not self.validate_players():
            return

        result = {
            'total_players': self.total_players_var.get(),
            'computer_players': self.computer_players_var.get(),
            'ladders': self.ladders_var.get(),
            'snakes': self.snakes_var.get()
        }
        # 패널은 콜백에서 제거
        if callable(self.on_submit):
            self.on_submit(result)

    def cancel_clicked(self):
        """취소 버튼 클릭 (앱 종료 콜백 호출)"""
        if callable(self.on_cancel):
            self.on_cancel()

class SnakeAndLadderGame:
    def __init__(self, root):
        self.root = root
        self.root.title("뱀 사다리 게임")
        self.root.resizable(True, True)  # 창 크기 조절 가능하도록 변경

        self.player_images = [] # 포켓몬 이미지를 저장할 리스트
        
        # 게임 설정 변수 (초기값은 기본값 사용)
        self.num_players = DEFAULT_NUM_PLAYERS
        self.num_computer_players = DEFAULT_NUM_COMPUTER_PLAYERS
        self.num_snakes = DEFAULT_NUM_SNAKES
        self.num_ladders = DEFAULT_NUM_LADDERS

        # 게임 UI 위젯 (초기에는 없음)
        self.canvas = None
        self.canvas_frame = None
        self.control_frame = None
        self.dice_label = None
        self.roll_button = None
        self.status_label = None

        # 설정 패널 핸들
        self.setup_panel = None
        
        # 종횡비 고정을 위한 변수
        self.aspect_ratio_locked = False
        self.target_aspect_ratio = 1.0  # 1:1 (정사각형)
        self.resize_after_id = None

        # 초기 설정 화면 표시
        self.show_setup_dialog()

    def show_setup_dialog(self):
        """초기 설정 패널을 메인 윈도우에 표시"""
        # 기존 게임 UI가 있으면 제거
        self.destroy_game_ui()
        # 기존 설정 패널이 있으면 제거
        if self.setup_panel:
            self.setup_panel.destroy()
            self.setup_panel = None

        # 새 설정 패널 표시
        self.setup_panel = SetupPanel(self.root, on_submit=self.on_setup_submit, on_cancel=self.on_setup_cancel)

    def on_setup_submit(self, result):
        """설정 패널에서 '시작' 클릭 시 처리"""
        self.num_players = result['total_players']
        self.num_computer_players = result['computer_players']
        self.num_snakes = result['snakes']
        self.num_ladders = result['ladders']

        # 설정 패널 제거 후 게임 UI 생성 및 시작
        if self.setup_panel:
            self.setup_panel.destroy()
            self.setup_panel = None

        self.build_game_ui()
        self.start_new_game()

    def on_setup_cancel(self):
        """설정 패널에서 '취소' 클릭 시 앱 종료"""
        self.root.destroy()

    def build_game_ui(self):
        """게임 UI를 생성하여 메인 윈도우에 배치"""
        # 캔버스 프레임 (리사이징을 위해 프레임에 담음)
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 캔버스
        self.canvas = tk.Canvas(self.canvas_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 윈도우 리사이징 이벤트 바인딩
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        
        # 윈도우 리사이징 시 종횡비 유지
        self.aspect_ratio_locked = True
        self.root.bind('<Configure>', self.on_window_resize)

        # 컨트롤 프레임
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(pady=5)

        self.dice_label = tk.Label(self.control_frame, text="주사위: -", font=('Helvetica', 14))
        self.dice_label.pack(side=tk.LEFT, padx=10)

        self.roll_button = tk.Button(self.control_frame, text="주사위 굴리기", font=('Helvetica', 14), command=self.play_turn)
        self.roll_button.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(self.root, text="", font=('Helvetica', 14), fg='blue')
        self.status_label.pack(pady=10)

    def on_window_resize(self, event):
        """윈도우 리사이징 시 종횡비를 유지합니다"""
        if not self.aspect_ratio_locked or event.widget != self.root:
            return
        
        # 리사이징 중복 호출 방지
        if self.resize_after_id:
            self.root.after_cancel(self.resize_after_id)
        
        # 짧은 지연 후 종횡비 조정 (연속적인 리사이징 이벤트 처리)
        self.resize_after_id = self.root.after(10, self.adjust_aspect_ratio)

    def adjust_aspect_ratio(self):
        """윈도우의 종횡비를 조정합니다"""
        self.resize_after_id = None
        
        # 현재 윈도우 크기 가져오기
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        
        # 목표 종횡비에 맞춰 크기 조정
        # 캔버스는 정사각형이어야 하지만, 컨트롤 UI를 위한 추가 높이 필요
        # 전체 윈도우의 종횡비를 대략 1:1.15 정도로 유지 (컨트롤 패널 고려)
        
        # 너비를 기준으로 적절한 높이 계산 (1:1.2 비율)
        target_height = int(current_width * 1.2)
        
        # 높이가 너무 작으면 최소값 적용
        if target_height < 400:
            target_height = 400
            current_width = int(target_height / 1.2)
        
        # 크기가 현재와 많이 다르면 조정
        if abs(current_height - target_height) > 5:
            self.root.geometry(f"{current_width}x{target_height}")

    def on_canvas_resize(self, event):
        """캔버스 리사이징 이벤트 핸들러 - 보드를 다시 그립니다"""
        if hasattr(self, 'game_over') and not self.game_over and hasattr(self, 'snakes'):
            # 게임이 진행 중일 때만 보드를 다시 그립니다
            self.draw_board()

    def destroy_game_ui(self):
        """기존 게임 UI 위젯 제거"""
        widgets = [self.canvas_frame, self.control_frame, self.status_label]
        for w in widgets:
            try:
                if w is not None:
                    w.destroy()
            except Exception:
                pass
        self.canvas = None
        self.control_frame = None
        self.dice_label = None
        self.roll_button = None
        self.status_label = None

    @property
    def computer_player_start_index(self):
        """컴퓨터 플레이어의 시작 인덱스 계산"""
        return self.num_players - self.num_computer_players

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

    def reset_roll_button(self):
        """주사위 굴리기 버튼을 초기 상태로 재설정"""
        self.roll_button.config(state=tk.NORMAL, text="주사위 굴리기", command=self.play_turn)

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
        self.reset_roll_button()

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

    def get_current_cell_size(self):
        """현재 캔버스 크기에 맞는 셀 크기를 계산합니다"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        # 가로와 세로 중 작은 값을 기준으로 셀 크기 결정
        size = min(canvas_width, canvas_height)
        return max(size // GRID_DIM, 20)  # 최소 셀 크기는 20px

    def get_coords(self, square):
        """칸 번호를 Canvas 좌표로 변환합니다."""
        cell_size = self.get_current_cell_size()
        canvas_height = self.canvas.winfo_height()
        
        square -= 1
        row = square // GRID_DIM
        col = square % GRID_DIM
        
        if row % 2 != 0:  # 홀수 줄 (1, 3, 5...)은 오른쪽에서 왼쪽으로
            col = GRID_DIM - 1 - col
            
        x = col * cell_size
        y = canvas_height - (row + 1) * cell_size
        return x + cell_size / 2, y + cell_size / 2

    def draw_board(self):
        """보드, 칸 번호, 뱀과 사다리를 그립니다."""
        self.canvas.delete("all")
        cell_size = self.get_current_cell_size()
        
        # 폰트 크기를 셀 크기에 비례하게 조정
        font_size = max(8, int(cell_size / 6))
        
        for i in range(GRID_DIM):
            for j in range(GRID_DIM):
                x1, y1 = j * cell_size, i * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                fill_color = "#F0E68C" if (i + j) % 2 == 0 else "#FFFACD"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="black")
                
                square_num = (GRID_DIM - i - 1) * GRID_DIM
                if (GRID_DIM - i - 1) % 2 == 0:
                    square_num += j + 1
                else:
                    square_num += GRID_DIM - j
                
                self.canvas.create_text(x1 + cell_size/2, y1 + cell_size/2, text=str(square_num), font=('Helvetica', font_size))

        # 화살표 크기를 셀 크기에 비례하게 조정
        line_width = max(2, int(cell_size / 10))
        arrow_size = max(8, int(cell_size / 3))
        arrowshape = (arrow_size, arrow_size + 4, arrow_size // 2)
        
        # 사다리 그리기 (파란색, 더 굵고 화살표 크게)
        for start, end in self.ladders.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='#0066CC', width=line_width, arrow=tk.LAST, 
                                  arrowshape=arrowshape, smooth=True)

        # 뱀 그리기 (빨간색, 더 굵고 화살표 크게)
        for start, end in self.snakes.items():
            x1, y1 = self.get_coords(start)
            x2, y2 = self.get_coords(end)
            self.canvas.create_line(x1, y1, x2, y2, fill='#CC0000', width=line_width, arrow=tk.LAST, 
                                  arrowshape=arrowshape, smooth=True)
            
        self.draw_players()

    def load_player_sprites(self):
        """PokeAPI에서 플레이어 수만큼 랜덤 포켓몬 이미지를 불러옵니다."""
        self.player_image_data = []  # 원본 PIL 이미지 저장
        self.player_images = []  # 렌더링용 PhotoImage 저장
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

                # 이미지 다운로드 (원본 저장)
                img_data = requests.get(sprite_url, timeout=5).content
                img = Image.open(io.BytesIO(img_data))
                self.player_image_data.append(img)
            
            # 현재 셀 크기에 맞게 리사이즈
            self.resize_player_images()
            
            print(f"성공적으로 {self.num_players}마리의 포켓몬을 불러왔습니다.")

        except Exception as e:
            print(f"포켓몬 이미지 로딩 실패: {e}. 기본 말로 대체합니다.")
            self.player_image_data = []
            self.player_images = [] # 실패 시 이미지 리스트 초기화

    def resize_player_images(self):
        """플레이어 이미지를 현재 셀 크기에 맞게 리사이즈합니다"""
        if not self.player_image_data:
            return
        
        cell_size = self.get_current_cell_size()
        sprite_size = max(20, int(cell_size * 0.6))  # 셀 크기의 60%
        
        self.player_images = []
        for img in self.player_image_data:
            resized = img.resize((sprite_size, sprite_size), Image.Resampling.LANCZOS)
            self.player_images.append(ImageTk.PhotoImage(resized))

    def draw_players(self):
        """플레이어 말을 그립니다. (포켓몬 또는 기본 도형)"""
        self.canvas.delete("player")
        cell_size = self.get_current_cell_size()
        offset_dist = max(6, int(cell_size / 8))
        player_radius = max(5, int(cell_size / 10))
        
        # 이미지가 있으면 리사이즈
        if self.player_image_data:
            self.resize_player_images()
        
        for i, pos in enumerate(self.player_positions):
            # 100을 넘은 플레이어는 100 위치에 그립니다
            draw_pos = min(pos, BOARD_SIZE)
            x, y = self.get_coords(draw_pos)
            offset = (i - (self.num_players - 1) / 2) * offset_dist

            if self.player_images and len(self.player_images) == self.num_players:
                self.canvas.create_image(x + offset, y, image=self.player_images[i], tags="player")
            else:
                self.canvas.create_oval(x - player_radius + offset, y - player_radius, 
                                        x + player_radius + offset, y + player_radius, 
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

        # 다음 턴도 컴퓨터라면 자동으로 이어서 진행
        if not self.game_over and self.is_computer_player(self.current_player):
            self.root.after(1000, self.computer_turn)
        else:
            # 사람 차례가 되면 버튼을 다시 활성화
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
