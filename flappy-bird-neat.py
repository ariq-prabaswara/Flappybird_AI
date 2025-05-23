import pygame
import neat
import time
import os
import random
pygame.font.init()

WIN_WIDTH = 500
WIN_HEIGHT = 800

BIRD_IMGS = [pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "bird1.png"))),
             pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "bird2.png"))),
             pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "bird3.png")))]
PIPE_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "pipe.png")))
BASE_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "base.png")))
BG_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs", "bg.png")))

STAT_FONT = pygame.font.SysFont("comicsans", 20)

GEN = 0 # Delete this later
HIGH_SCORE = 0

class Bird:
    IMGS = BIRD_IMGS
    MAX_ROTATION = 25
    ROT_VEL = 20
    ANIMATION_TIME = 3

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tilt = 0
        self.tick_count = 0
        self.vel = 0
        self.height = self.y
        self.img_count = 0
        self.img = self.IMGS[0]

    def jump(self):
        self.vel = -10.5
        self.tick_count = 0
        self.height = self.y
    
    def move(self):
        self.tick_count += 1

        d = self.vel*self.tick_count + 1.5*self.tick_count**2

        if d >= 16:
            d = 16

        if d < 0:
            d -= 2

        self.y = self.y + d

        if d < 0 or self.y < self.height + 50:
            if self.tilt < self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        else:
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL
    
    def draw(self, win):
        self.img_count += 1

        if self.img_count < self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count < self.ANIMATION_TIME*2:
            self.img = self.IMGS[1]
        elif self.img_count < self.ANIMATION_TIME*3:
            self.img = self.IMGS[2]
        elif self.img_count < self.ANIMATION_TIME*4:
            self.img = self.IMGS[1]
        elif self.img_count == self.ANIMATION_TIME*4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0
    
        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME*2
        
        rotated_image = pygame.transform.rotate(self.img, self.tilt)
        new_rect = rotated_image.get_rect(center=self.img.get_rect(topleft = (self.x, self.y)).center)
        win.blit(rotated_image, new_rect.topleft)

    def get_mask(self):
        return pygame.mask.from_surface(self.img)
    

class Pipe:
    GAP = 170
    VEL = 5

    def __init__(self, x):
        self.x = x
        self.height = 0

        self.top = 0
        self.bottom = 0
        self.PIPE_TOP = pygame.transform.flip(PIPE_IMG, False, True)
        self.PIPE_BOTTOM = PIPE_IMG

        self.passed = False
        self.set_height()

    def set_height(self):
        self.height = random.randrange(50, 450)
        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + self.GAP

    def move(self):
        self.x -= self.VEL

    def draw(self, win):
        win.blit(self.PIPE_TOP, (self.x, self.top))
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))
    
    #　Check pixel perfect collision between bird and pipe
    def collide(self, bird):
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)
        
        top_offset = (self.x - bird.x, int(self.top - round(bird.y)))
        bottom_offset = (self.x - bird.x, int(self.bottom - round(bird.y)))

        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask, top_offset)

        if t_point or b_point:
            return True
        
        return False


class Base:
    VEL = 5
    WIDTH = BASE_IMG.get_width()
    IMG = BASE_IMG

    def __init__(self, y):
        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH

    def move(self):
        self.x1 -= self.VEL
        self.x2 -= self.VEL

        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH

        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH
    
    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))

def draw_window(win, birds, pipes, base, score, gen):
    win.blit(BG_IMG, (0,0))
    
    for pipe in pipes:
        pipe.draw(win)
    
    # Display Score
    text = STAT_FONT.render("Score: " + str(score), 1, (255,255,255))
    win.blit(text, (WIN_WIDTH - 10 - text.get_width(), 10))

    # Display High Score
    text = STAT_FONT.render("High Score: " + str(HIGH_SCORE), 1, (255,255,255))
    win.blit(text, (WIN_WIDTH - 10 - text.get_width(), 10 + text.get_height()))

    # Display Generation
    text = STAT_FONT.render("Generation: " + str(gen), 1, (255,255,255))
    win.blit(text, (10, 10))

    # Display Alive
    text = STAT_FONT.render("Alive: " + str(len(birds)), 1, (255,255,255))
    win.blit(text, (10, 10 + text.get_height()))

    # Draw Base
    base.draw(win)

    # Draw the birds
    for bird in birds:
        bird.draw(win)

    pygame.display.update()

def main(genomes, config):
    global GEN
    global HIGH_SCORE
    GEN += 1
    nets = []       # Neural network that control the bird
    ge = []         # Genome List
    birds = []

    for _, g in genomes:                # Need _, because gemone is a tuple that contain index like (1, g)
        net = neat.nn.FeedForwardNetwork.create(g, config) # Neural Network for The genome
        nets.append(net)
        birds.append(Bird(230, 350))    # Starting position for all birds
        g.fitness = 0                   # The initial fitness score for the bird
        ge.append(g) 

    base = Base(730)
    pipes = [Pipe(600)]

    win = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    clock = pygame.time.Clock()

    score = 0

    run = True
    while run:
        clock.tick(144)      # FPS
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                quit()

        # Check which pipe we are looking the distance for
        # If we passed the first pipe (pipe_ind = 0) then, we are looking at the next pipe (pipe_ind = 1)
        pipe_ind = 0    
        if len(birds) > 0:
            if len(pipes) > 1 and birds[0].x > pipes[0].x + pipes[0].PIPE_TOP.get_width():
                pipe_ind = 1
        
        # If no more bird survive
        else:   
            run = False
            if score > HIGH_SCORE:
                HIGH_SCORE = score
            break

                
        for x, bird in enumerate(birds):
            bird.move()
            ge[x].fitness += 0.1 # Giving bird fitness score for every second it moves
            
            # Calculate Neural network for jump
            output = nets[x].activate((bird.y, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom))) 
            
            if output[0] > 0.5:
                bird.jump()

        add_pipe = False
        rem = []
        for pipe in pipes:
            for x, bird in enumerate(birds):  # Ask this later in chat GPT 
                
                # Collision Check
                if pipe.collide(bird):
                    ge[x].fitness -= 1 # Reduce the fitness score if it collide with the pipe
                    birds.pop(x) # No longer processing the bird that have collided
                    nets.pop(x)
                    ge.pop(x)
                
                # If the bird passed the pipe
                if not pipe.passed and pipe.x < bird.x:
                    pipe.passed = True
                    add_pipe = True 
            
            # If Pipe pass the screen, put the pipe on rem for deletion
            if pipe.x + pipe.PIPE_TOP.get_width() < 0:
                rem.append(pipe)

            pipe.move() 

        if add_pipe:
            score += 1
            for g in ge:
                g.fitness += 5  # Giving 5 score to the bird that successfully pass the pipe

            pipes.append(Pipe(600))
            
        for r in rem:
            pipes.remove(r)

        for x, bird in enumerate(birds):
            
            # If the bird falls to the ground
            if bird.y + bird.img.get_height() >= base.y or bird.y < 0:
                birds.pop(x)
                nets.pop(x)
                ge.pop(x) 

        if score > 50:
            break

        base.move()
        draw_window(win, birds, pipes, base, score, GEN)


# NEAT Part
def run(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_path)
    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(main,50)

if __name__ == "__main__":
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")
    run(config_path)

        