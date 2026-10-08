import subprocess
import sys
import pygame

VERSION = "0.3"

# ============================================================
#  НАСТРОЙКИ
# ============================================================
W, H = 1120, 700
TILE = 60
COLS, ROWS = 9, 8
GRID_X, GRID_Y = 24, 80
PANEL_X = GRID_X + COLS * TILE + 30
PANEL_W = W - PANEL_X - 24
STEP_MS = 320  # скорость анимации (мс на один шаг)

BG = (24, 28, 26)
TILE_A = (58, 84, 52)
TILE_B = (52, 76, 47)
PANEL = (36, 42, 38)
TEXT = (230, 230, 220)
MUTED = (150, 160, 150)
GREEN = (110, 200, 120)
RED = (235, 110, 100)
YELLOW = (235, 200, 90)
BUTTON = (70, 120, 80)
BUTTON_HOVER = (90, 150, 100)
CODE_BG = (18, 20, 24)

STARTER = "# Напиши команды здесь\n"

# ============================================================
#  УРОВНИ
#  Чтобы добавить новый уровень, скопируй любой блок и измени его.
# ============================================================
LEVELS = [
    {
        "title": "День 1: Найди 3 палки",
        "topic": "Команды и порядок",
        "theory": (
            "Программа - это список команд. Python выполняет их по очереди, "
            "сверху вниз, строчка за строчкой. У каждой команды есть имя и скобки ()."
        ),
        "example": ["идти_вправо()", "идти_вправо()", "взять()"],
        "text": "Собери 3 палки для костра. Код выполняется сверху вниз, строчка за строчкой.",
        "commands": [
            ("идти_вправо()   идти_влево()", True),
            ("идти_вверх()    идти_вниз()", True),
            ("взять()   - взять палку с клетки", True),
            ("Скобки () обязательны!", False),
        ],
        "start": (0, 0),
        "sticks": [(3, 0), (3, 2), (6, 2)],
        "goal": 3,
        "max_lines": None,
        "win": "Победа! Ты написал свою первую программу: список команд, которые выполняются по порядку.",
    },
    {
        "title": "День 2: Дорога и цикл for",
        "topic": "Цикл for",
        "theory": (
            "Если действие нужно повторить много раз, не копируй строки, а используй цикл. "
            "range(3) значит «3 раза». Всё, что написано с отступом (4 пробела) под for, "
            "будет повторяться. Отступ ставится клавишей Tab."
        ),
        "example": ["for i in range(3):", "    идти_вправо()", "    взять()"],
        "text": "Вдоль дороги лежат 8 палок. Код должен быть не длиннее 4 строк, значит, нужен цикл for.",
        "commands": [
            ("идти_вправо()   идти_вниз()   взять()", True),
            ("for i in range(5):  - повторить 5 раз", True),
            ("Максимум 4 строки кода (комментарии не считаются)", False),
        ],
        "start": (0, 0),
        "sticks": [(x, 0) for x in range(1, 9)],
        "goal": 8,
        "max_lines": 4,
        "win": "Победа! Цикл for заменил 16 строк на 3. Программисты любят делать меньше работы.",
    },
    {
        "title": "День 3: Умный сбор и if",
        "topic": "Условие if",
        "theory": (
            "Иногда действие нужно выполнять только при условии. Команда есть_палка() "
            "отвечает True (да) или False (нет). Блок с отступом под if выполнится, "
            "только если ответ True. Если взять() там, где палки нет, будет ошибка."
        ),
        "example": ["if есть_палка():", "    взять()"],
        "text": "Палки лежат не на каждой клетке. Пройди весь ряд и бери палку только там, где она есть.",
        "commands": [
            ("идти_вправо()   взять()", True),
            ("есть_палка()  - True, если на клетке палка", True),
            ("if условие:  - выполнить, только если True", True),
        ],
        "start": (0, 3),
        "sticks": [(1, 3), (3, 3), (4, 3), (6, 3), (8, 3)],
        "goal": 5,
        "max_lines": None,
        "win": "Победа! Теперь твоя программа принимает решения сама: if + цикл for - мощная связка.",
    },
]


class GameError(Exception):
    """Ошибка игрового мира (врезался в стену, нечего брать)."""


def get_clipboard():
    """Возвращает текст из буфера обмена (для вставки)."""
    try:
        if sys.platform == "darwin":
            return subprocess.run(["pbpaste"], capture_output=True, timeout=2).stdout.decode("utf-8", "ignore")
        return pygame.scrap.get_text() or ""
    except Exception:
        return ""


# ============================================================
#  МИР И ЗАПУСК КОДА ИГРОКА
# ============================================================
class World:
    def __init__(self, level):
        self.x, self.y = level["start"]
        self.sticks = set(level["sticks"])
        self.taken = 0

    def snapshot(self):
        return (self.x, self.y, frozenset(self.sticks), self.taken)


def player_line(tb):
    """Находит номер строки в коде игрока, где случилась ошибка."""
    line = None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<игрок>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def run_code(code, level):
    """Выполняет код игрока. Возвращает (кадры анимации, вывод print, ошибка)."""
    sim = World(level)
    frames = [sim.snapshot()]
    output = []

    # Проверка длины кода (для уровней, где нужен цикл)
    limit = level.get("max_lines")
    if limit:
        meaningful = [ln for ln in code.split("\n") if ln.strip() and not ln.strip().startswith("#")]
        if len(meaningful) > limit:
            return frames, output, (
                f"Слишком длинный код: {len(meaningful)} строк, а можно максимум {limit}. "
                f"Подсказка: повтори действие циклом for."
            )

    def add_frame():
        frames.append(sim.snapshot())
        if len(frames) > 500:
            raise GameError("Слишком много шагов (больше 500). Возможно, цикл не заканчивается?")

    def move(dx, dy):
        nx, ny = sim.x + dx, sim.y + dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            raise GameError("Персонаж упёрся в край карты и не может пройти дальше.")
        sim.x, sim.y = nx, ny
        add_frame()

    def take():
        if (sim.x, sim.y) not in sim.sticks:
            raise GameError("Здесь нечего брать: на этой клетке нет палки. Подсказка: проверь её через if есть_палка():")
        sim.sticks.remove((sim.x, sim.y))
        sim.taken += 1
        add_frame()

    def has_stick():
        return (sim.x, sim.y) in sim.sticks

    def game_print(*args):
        output.append(" ".join(str(a) for a in args))

    safe_builtins = {
        "range": range, "len": len, "int": int, "str": str, "float": float,
        "bool": bool, "list": list, "dict": dict, "min": min, "max": max,
        "abs": abs, "sum": sum, "enumerate": enumerate, "print": game_print,
        "True": True, "False": False, "None": None,
    }
    env = {
        "__builtins__": safe_builtins,
        "идти_вправо": lambda: move(1, 0),
        "идти_влево": lambda: move(-1, 0),
        "идти_вверх": lambda: move(0, -1),
        "идти_вниз": lambda: move(0, 1),
        "взять": take,
        "есть_палка": has_stick,
    }

    try:
        compiled = compile(code, "<игрок>", "exec")
    except SyntaxError as e:
        msg = (
            f"Синтаксическая ошибка в строке {e.lineno}. Проверь скобки, "
            f"двоеточия и отступы. (Python пишет: {e.msg})"
        )
        return frames, output, msg

    counter = [0]

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != "<игрок>":
            return None
        if event == "line":
            counter[0] += 1
            if counter[0] > 20000:
                raise GameError("Программа работает слишком долго. Нет ли бесконечного цикла?")
        return tracer

    error = None
    try:
        sys.settrace(tracer)
        exec(compiled, env)
    except Exception as e:
        line = player_line(e.__traceback__)
        where = f"Строка {line}: " if line else ""
        if isinstance(e, GameError):
            error = where + str(e)
        elif isinstance(e, NameError):
            name = getattr(e, "name", "?")
            error = where + f"Python не знает слова «{name}». Проверь опечатки и скобки ()."
        elif isinstance(e, TypeError):
            error = where + f"Неверное использование команды. (Python пишет: {e})"
        else:
            error = where + f"{type(e).__name__}: {e}"
    finally:
        sys.settrace(None)

    return frames, output, error


# ============================================================
#  РЕДАКТОР КОДА
# ============================================================
class Editor:
    def __init__(self, rect, font):
        self.rect = rect
        self.font = font
        self.lh = font.get_linesize() + 2
        self.set_text(STARTER)

    def set_text(self, text):
        self.lines = text.split("\n")
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])
        self.top = 0

    def text(self):
        return "\n".join(self.lines)

    def insert(self, s):
        line = self.lines[self.row]
        self.lines[self.row] = line[:self.col] + s + line[self.col:]
        self.col += len(s)

    def paste(self, text):
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
        if not text:
            return
        parts = text.split("\n")
        line = self.lines[self.row]
        before, after = line[:self.col], line[self.col:]
        if len(parts) == 1:
            self.lines[self.row] = before + parts[0] + after
            self.col += len(parts[0])
            return
        new_lines = [before + parts[0]] + parts[1:-1] + [parts[-1] + after]
        self.lines[self.row:self.row + 1] = new_lines
        self.row += len(parts) - 1
        self.col = len(parts[-1])

    def newline(self):
        line = self.lines[self.row]
        before, after = line[:self.col], line[self.col:]
        indent = len(before) - len(before.lstrip(" "))
        if before.rstrip().endswith(":"):
            indent += 4
        self.lines[self.row] = before
        self.lines.insert(self.row + 1, " " * indent + after)
        self.row += 1
        self.col = indent

    def backspace(self):
        if self.col > 0:
            line = self.lines[self.row]
            self.lines[self.row] = line[:self.col - 1] + line[self.col:]
            self.col -= 1
        elif self.row > 0:
            prev = self.lines[self.row - 1]
            self.col = len(prev)
            self.lines[self.row - 1] = prev + self.lines[self.row]
            del self.lines[self.row]
            self.row -= 1

    def key(self, event):
        k = event.key
        if k == pygame.K_RETURN:
            self.newline()
        elif k == pygame.K_BACKSPACE:
            self.backspace()
        elif k == pygame.K_TAB:
            self.insert("    ")
        elif k == pygame.K_LEFT:
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif k == pygame.K_RIGHT:
            if self.col < len(self.lines[self.row]):
                self.col += 1
            elif self.row < len(self.lines) - 1:
                self.row += 1
                self.col = 0
        elif k == pygame.K_UP and self.row > 0:
            self.row -= 1
            self.col = min(self.col, len(self.lines[self.row]))
        elif k == pygame.K_DOWN and self.row < len(self.lines) - 1:
            self.row += 1
            self.col = min(self.col, len(self.lines[self.row]))

    def draw(self, screen, active):
        pygame.draw.rect(screen, CODE_BG, self.rect, border_radius=8)
        pygame.draw.rect(screen, GREEN if active else MUTED, self.rect, 2, border_radius=8)
        visible = (self.rect.height - 16) // self.lh
        if self.row < self.top:
            self.top = self.row
        if self.row >= self.top + visible:
            self.top = self.row - visible + 1
        clip = screen.get_clip()
        screen.set_clip(self.rect.inflate(-4, -4))
        for i in range(visible):
            n = self.top + i
            if n >= len(self.lines):
                break
            y = self.rect.y + 8 + i * self.lh
            num = self.font.render(str(n + 1), True, (90, 100, 95))
            screen.blit(num, (self.rect.x + 30 - num.get_width(), y))
            line = self.lines[n]
            color = (120, 140, 120) if line.strip().startswith("#") else TEXT
            screen.blit(self.font.render(line, True, color), (self.rect.x + 42, y))
            if n == self.row and active and (pygame.time.get_ticks() // 500) % 2 == 0:
                cx = self.rect.x + 42 + self.font.size(line[:self.col])[0]
                pygame.draw.line(screen, YELLOW, (cx, y), (cx, y + self.lh - 2), 2)
        screen.set_clip(clip)


# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================
def wrap(text, font, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if font.size(t)[0] <= width:
                cur = t
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_wrapped(screen, text, font, color, x, y, width, gap=4):
    for line in wrap(text, font, width):
        screen.blit(font.render(line, True, color), (x, y))
        y += font.get_linesize() + gap
    return y


def draw_button(screen, rect, label, font):
    hover = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, BUTTON_HOVER if hover else BUTTON, rect, border_radius=8)
    img = font.render(label, True, (255, 255, 255))
    screen.blit(img, img.get_rect(center=rect.center))


def draw_world(screen, state):
    x, y, sticks, taken = state
    for r in range(ROWS):
        for c in range(COLS):
            color = TILE_A if (r + c) % 2 == 0 else TILE_B
            pygame.draw.rect(screen, color, (GRID_X + c * TILE, GRID_Y + r * TILE, TILE, TILE))
    for (sx, sy) in sticks:
        px, py = GRID_X + sx * TILE, GRID_Y + sy * TILE
        pygame.draw.line(screen, (140, 95, 50), (px + 14, py + TILE - 14), (px + TILE - 14, py + 14), 7)
        pygame.draw.line(screen, (170, 120, 70), (px + 14, py + TILE - 14), (px + TILE - 14, py + 14), 3)
    cx = GRID_X + x * TILE + TILE // 2
    cy = GRID_Y + y * TILE + TILE // 2
    pygame.draw.circle(screen, (70, 130, 200), (cx, cy), 21)
    pygame.draw.circle(screen, (240, 215, 180), (cx, cy - 4), 12)
    pygame.draw.circle(screen, (30, 30, 30), (cx - 4, cy - 6), 2)
    pygame.draw.circle(screen, (30, 30, 30), (cx + 4, cy - 6), 2)
    pygame.draw.rect(screen, (90, 90, 90), (GRID_X, GRID_Y, COLS * TILE, ROWS * TILE), 2)


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================
class State:
    pass


def main():
    pygame.init()
    pygame.key.start_text_input()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Зомби и Python")
    clock = pygame.time.Clock()

    ui = pygame.font.SysFont("arial,helvetica,dejavusans", 20)
    big = pygame.font.SysFont("arial,helvetica,dejavusans", 30, bold=True)
    mono = pygame.font.SysFont("menlo,consolas,couriernew,dejavusansmono,monospace", 19)

    editor = Editor(pygame.Rect(PANEL_X, 282, PANEL_W, 238), mono)
    run_btn = pygame.Rect(PANEL_X, 535, 150, 44)
    reset_btn = pygame.Rect(PANEL_X + 160, 535, 130, 44)
    paste_btn = pygame.Rect(PANEL_X + 300, 535, 100, 44)
    theory_btn = pygame.Rect(PANEL_X + 410, 535, 92, 44)
    msg_rect = pygame.Rect(GRID_X, GRID_Y + ROWS * TILE + 14, COLS * TILE, 96)
    next_btn = pygame.Rect(msg_rect.right - 230, msg_rect.bottom - 50, 218, 40)
    intro_rect = pygame.Rect(140, 90, 840, 520)
    start_btn = pygame.Rect(intro_rect.centerx - 130, intro_rect.bottom - 70, 260, 48)

    S = State()

    def load_level(i):
        S.idx_level = i
        S.level = LEVELS[i]
        S.start = World(S.level).snapshot()
        S.display = S.start
        S.frames, S.output, S.error = [], [], None
        S.step, S.last_tick = 0, 0
        S.won = False
        S.mode = "intro"
        S.msg, S.color = "Напиши код и нажми «Запустить» (или Ctrl+Enter).", MUTED
        editor.set_text(STARTER)

    def start_run():
        S.frames, S.output, S.error = run_code(editor.text(), S.level)
        S.display = S.frames[0]
        S.step = 1
        S.last_tick = pygame.time.get_ticks()
        S.mode = "playing"
        S.msg, S.color = "Выполняю твой код...", YELLOW

    def reset():
        S.display = S.start
        S.mode = "edit"
        S.output = []
        S.msg, S.color = "Мир сброшен. Исправь код и запусти снова.", MUTED

    load_level(0)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                ctrl = event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
                if S.mode == "intro":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        S.mode = "edit"
                elif ctrl and event.key == pygame.K_RETURN:
                    if S.mode == "edit":
                        start_run()
                elif ctrl and event.key == pygame.K_v:
                    if S.mode == "edit":
                        editor.paste(get_clipboard())
                elif S.mode == "edit":
                    editor.key(event)

            elif event.type == pygame.TEXTINPUT and S.mode == "edit":
                if "\n" not in event.text and "\r" not in event.text:
                    editor.insert(event.text)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if S.mode == "intro":
                    if start_btn.collidepoint(event.pos):
                        S.mode = "edit"
                elif run_btn.collidepoint(event.pos) and S.mode == "edit":
                    start_run()
                elif reset_btn.collidepoint(event.pos):
                    reset()
                elif paste_btn.collidepoint(event.pos) and S.mode == "edit":
                    editor.paste(get_clipboard())
                elif theory_btn.collidepoint(event.pos) and S.mode == "edit":
                    S.mode = "intro"
                elif (next_btn.collidepoint(event.pos) and S.won and S.mode == "edit"
                      and S.idx_level < len(LEVELS) - 1):
                    load_level(S.idx_level + 1)

        # Анимация выполнения
        if S.mode == "playing":
            now = pygame.time.get_ticks()
            if now - S.last_tick >= STEP_MS:
                S.last_tick = now
                if S.step < len(S.frames):
                    S.display = S.frames[S.step]
                    S.step += 1
                else:
                    S.mode = "edit"
                    taken = S.display[3]
                    goal = S.level["goal"]
                    if S.error:
                        S.msg, S.color = S.error, RED
                    elif taken >= goal:
                        S.won = True
                        if S.idx_level == len(LEVELS) - 1:
                            S.msg, S.color = S.level["win"] + " Все уровни пройдены!", GREEN
                        else:
                            S.msg, S.color = S.level["win"], GREEN
                    else:
                        S.msg, S.color = (
                            f"Собрано палок: {taken}/{goal}. Нужно больше. Сбрось мир и попробуй ещё.",
                            YELLOW,
                        )

        # ---------- Рисование ----------
        level = S.level
        screen.fill(BG)
        screen.blit(big.render(level["title"], True, TEXT), (GRID_X, 24))
        draw_world(screen, S.display)

        counter = ui.render(f"Палки: {S.display[3]}/{level['goal']}", True, YELLOW)
        screen.blit(counter, (GRID_X + COLS * TILE - counter.get_width(), 52))
        screen.blit(ui.render(f"версия {VERSION}  |  уровень {S.idx_level + 1} из {len(LEVELS)}", True, (90, 100, 95)),
                    (PANEL_X, 24))

        # Сообщение под картой
        pygame.draw.rect(screen, PANEL, msg_rect, border_radius=8)
        msg_width = msg_rect.width - 24
        if S.won and S.idx_level < len(LEVELS) - 1:
            msg_width -= 0
        draw_wrapped(screen, S.msg, ui, S.color, msg_rect.x + 12, msg_rect.y + 8, msg_width)
        if S.won and S.idx_level < len(LEVELS) - 1 and S.mode == "edit":
            draw_button(screen, next_btn, "Следующий уровень", ui)

        # Правая панель: задание и команды
        pygame.draw.rect(screen, PANEL, (PANEL_X, 56, PANEL_W, 214), border_radius=8)
        y = draw_wrapped(screen, level["text"], ui, TEXT, PANEL_X + 12, 66, PANEL_W - 24)
        y += 6
        for line, is_code in level["commands"]:
            font = mono if is_code else ui
            screen.blit(font.render(line, True, GREEN if is_code else MUTED), (PANEL_X + 12, y))
            y += 24

        editor.draw(screen, S.mode == "edit")
        draw_button(screen, run_btn, "Запустить", ui)
        draw_button(screen, reset_btn, "Сбросить", ui)
        draw_button(screen, paste_btn, "Вставить", ui)
        draw_button(screen, theory_btn, "Теория", ui)

        # Вывод print()
        out_rect = pygame.Rect(PANEL_X, 595, PANEL_W, 85)
        pygame.draw.rect(screen, CODE_BG, out_rect, border_radius=8)
        screen.blit(ui.render("Вывод print():", True, MUTED), (out_rect.x + 10, out_rect.y + 6))
        for i, line in enumerate(S.output[-2:]):
            screen.blit(mono.render(line, True, TEXT), (out_rect.x + 10, out_rect.y + 32 + i * 22))

        # Экран с теорией
        if S.mode == "intro":
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 175))
            screen.blit(dim, (0, 0))
            pygame.draw.rect(screen, PANEL, intro_rect, border_radius=14)
            pygame.draw.rect(screen, GREEN, intro_rect, 2, border_radius=14)
            screen.blit(ui.render(f"Урок {S.idx_level + 1}", True, MUTED), (intro_rect.x + 30, intro_rect.y + 24))
            screen.blit(big.render(level["topic"], True, YELLOW), (intro_rect.x + 30, intro_rect.y + 50))
            y = draw_wrapped(screen, level["theory"], ui, TEXT, intro_rect.x + 30, intro_rect.y + 105,
                             intro_rect.width - 60, gap=6)
            screen.blit(ui.render("Пример:", True, MUTED), (intro_rect.x + 30, y + 16))
            ex_h = len(level["example"]) * 28 + 24
            ex_rect = pygame.Rect(intro_rect.x + 30, y + 46, intro_rect.width - 60, ex_h)
            pygame.draw.rect(screen, CODE_BG, ex_rect, border_radius=8)
            for i, line in enumerate(level["example"]):
                screen.blit(mono.render(line, True, GREEN), (ex_rect.x + 16, ex_rect.y + 12 + i * 28))
            draw_button(screen, start_btn, "Понятно, начать", ui)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
