import pygame
from paddle import Paddle
from ball import Ball
from bricks import Brick

class Game:
    def __init__(self):
        self.running = True
        self.score = 0
        self.lives = 3
        
        # ゲーム画面設定
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Block Breaker Game")
        self.clock = pygame.time.Clock()
        self.fps = 60
        
        # 色定義
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GREEN = (0, 255, 0)

    def start_game(self):
        # パドル初期化
        paddle_width = 100
        paddle_height = 20
        self.paddle = Paddle(
            self.width // 2 - paddle_width // 2,
            self.height - 50,
            paddle_width,
            paddle_height
        )
        
        # ボール初期化
        self.ball = Ball(
            self.width // 2,
            self.height // 2,
            10,
            self.WHITE
        )
        
        # ブロック初期化
        self.bricks = []
        brick_width = 75
        brick_height = 20
        rows = 5
        cols = 10
        
        for row in range(rows):
            for col in range(cols):
                x = col * (brick_width + 5) + 50
                y = row * (brick_height + 5) + 50
                self.bricks.append(Brick(x, y, brick_width, brick_height))

    def update(self):
        # キー入力処理
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.paddle.x > 0:
            self.paddle.move_left()
        if keys[pygame.K_RIGHT] and self.paddle.x < self.width - self.paddle.width:
            self.paddle.move_right()
        
        # ボール移動
        self.ball.move()
        
        # ボールと画面境界の衝突判定
        if self.ball.x <= self.ball.radius or self.ball.x >= self.width - self.ball.radius:
            self.ball.dx = -self.ball.dx
        if self.ball.y <= self.ball.radius:
            self.ball.dy = -self.ball.dy
        if self.ball.y >= self.height - self.ball.radius:
            self.lives -= 1
            if self.lives > 0:
                # ボールをリセット
                self.ball.reset(self.width // 2, self.height // 2)
            else:
                self.running = False
        
        # ボールとパドルの衝突判定
        ball_rect = pygame.Rect(self.ball.x - self.ball.radius, 
                               self.ball.y - self.ball.radius,
                               self.ball.radius * 2, 
                               self.ball.radius * 2)
        paddle_rect = pygame.Rect(self.paddle.x, self.paddle.y, 
                                 self.paddle.width, self.paddle.height)
        
        if ball_rect.colliderect(paddle_rect) and self.ball.dy > 0:
            self.ball.dy = -self.ball.dy
        
        # ボールとブロックの衝突判定
        for brick in self.bricks:
            if not brick.is_hit:
                brick_rect = pygame.Rect(brick.rect)
                if ball_rect.colliderect(brick_rect):
                    brick.hit()
                    self.ball.dy = -self.ball.dy
                    self.score += 10
                    break

    def draw(self):
        # 背景を黒で塗りつぶし
        self.screen.fill(self.BLACK)
        
        # パドル描画
        self.paddle.draw(self.screen)
        
        # ボール描画
        self.ball.draw(self.screen)
        
        # ブロック描画
        for brick in self.bricks:
            brick.draw(self.screen)
        
        # スコア表示
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, self.WHITE)
        self.screen.blit(score_text, (10, 10))
        
        lives_text = font.render(f"Lives: {self.lives}", True, self.WHITE)
        self.screen.blit(lives_text, (10, 50))
        
        # 画面更新
        pygame.display.flip()
        self.clock.tick(self.fps)

    def handle_events(self):
        # Handle user input and events
        pass

    def reset(self):
        # Reset the game state for a new game
        pass