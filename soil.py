import pygame
from settings import *
from pytmx.util_pygame import load_pygame
from support import *
from random import choice


class SoilTile(pygame.sprite.Sprite):
    def __init__(self, pos, surface, groups):
        super().__init__(groups)
        self.image = surface
        self.rect = self.image.get_rect(topleft=pos)
        self.z = LAYERS['soil']


class WaterTile(pygame.sprite.Sprite):
    def __init__(self, pos, surface, groups):
        super().__init__(groups)
        self.image = surface
        self.rect = self.image.get_rect(topleft=pos)
        self.z = LAYERS['soil water']


class Plant(pygame.sprite.Sprite):
    def __init__(self, plant_type, groups, soil, is_watered):
        super().__init__(groups)
        self.plant_type = plant_type
        self.frames = import_folder(f'graphics/fruit/{plant_type}')
        self.soil = soil
        self.is_watered = is_watered
        self.age = 0
        self.max_age = len(self.frames) - 2
        self.grow_speed = GROW_SPEED[plant_type]
        self.harvestable = False
        self.days_harvestable = 0
        self.plant_dead = False
        self.image = self.frames[self.age]
        self.y_offset = -16 if plant_type == 'corn' else -8
        self.rect = self.image.get_rect(
            midbottom=soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))
        self.z = LAYERS['ground plant']

    def grow(self):
        if self.is_watered(self.rect.center) and not self.plant_dead:
            self.age += self.grow_speed

            if int(self.age) > 0:
                self.z = LAYERS['main']
                self.hitbox = self.rect.copy().inflate(-26, -self.rect.height * 0.4)

            if self.age >= self.max_age:
                self.age = self.max_age
                self.harvestable = True
                self.days_harvestable += 1

        # if the plant has been harvestable for 2 full days, it dies.
        if self.days_harvestable == 3:
            self.age = self.max_age + 1
            self.plant_dead = True

        self.image = self.frames[int(self.age)]
        self.rect = self.image.get_rect(
            midbottom=self.soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))


class SoilLayer:
    def __init__(self, all_sprites, collision_sprites):
        self.all_sprites = all_sprites
        self.collision_sprites = collision_sprites
        self.soil_sprites = pygame.sprite.Group()
        self.water_sprites = pygame.sprite.Group()
        self.plant_sprites = pygame.sprite.Group()

        self.soil_surfaces = import_folder_dict('graphics/soil')
        self.water_surfaces = import_folder('graphics/soil_water/')

        self.create_soil_grid()
        self.create_hit_rects()

        self.hoe_sound = pygame.mixer.Sound('audio/hoe.wav')
        self.hoe_sound.set_volume(0.3)

        self.plant_sound = pygame.mixer.Sound('audio/plant.wav')
        self.plant_sound.set_volume(0.3)

    def create_soil_grid(self):
        ground = pygame.image.load('graphics/world/ground.png')
        h_tiles, v_tiles = ground.get_width() // TILE_SIZE, ground.get_height() // TILE_SIZE

        self.grid = [[[] for col in range(h_tiles)] for row in range(v_tiles)]

        for x, y, _ in load_pygame('graphics/map.tmx').get_layer_by_name('Farmable').tiles():
            self.grid[y][x].append('F')

    def create_hit_rects(self):
        self.hit_rects = []

        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                if 'F' in cell:
                    x = index_col * TILE_SIZE
                    y = index_row * TILE_SIZE
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    self.hit_rects.append(rect)

    def get_hit(self, pos):
        for rect in self.hit_rects:
            if rect.collidepoint(pos):
                pygame.mixer.stop()
                self.hoe_sound.play()

                x = rect.x // TILE_SIZE
                y = rect.y // TILE_SIZE

                if 'F' in self.grid[y][x]:
                    self.grid[y][x].append('X')
                    self.create_soil_tiles()

                    if self.raining:
                        self.water_all()

    def water(self, target_pos):
        for soil_sprite in self.soil_sprites.sprites():
            if soil_sprite.rect.collidepoint(target_pos):
                x = soil_sprite.rect.x // TILE_SIZE
                y = soil_sprite.rect.y // TILE_SIZE
                self.grid[y][x].append('W')
                pos = soil_sprite.rect.topleft
                surface = choice(self.water_surfaces)

                WaterTile(pos, surface, [self.all_sprites, self.water_sprites])

    def water_all(self):
        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                if 'X' in cell and 'W' not in cell:
                    cell.append('W')
                    x = index_col * TILE_SIZE
                    y = index_row * TILE_SIZE
                    WaterTile((x, y),
                              choice(self.water_surfaces),
                              [self.all_sprites, self.water_sprites])

    def remove_water(self):
        for sprite in self.water_sprites.sprites():
            sprite.kill()

        for row in self.grid:
            for cell in row:
                if 'W' in cell:
                    cell.remove('W')

    def check_if_watered(self, pos):
        x = pos[0] // TILE_SIZE
        y = pos[1] // TILE_SIZE
        cell = self.grid[y][x]

        is_watered = 'W' in cell

        return is_watered

    def plant_seed(self, target_pos, seed):
        for soil_sprite in self.soil_sprites.sprites():
            if soil_sprite.rect.collidepoint(target_pos):
                pygame.mixer.stop()
                self.plant_sound.play()

                x = soil_sprite.rect.x // TILE_SIZE
                y = soil_sprite.rect.y // TILE_SIZE

                if 'P' not in self.grid[y][x]:
                    self.grid[y][x].append('P')
                    Plant(seed,
                          [self.all_sprites, self.plant_sprites,
                              self.collision_sprites],
                          soil_sprite,
                          self.check_if_watered)

    def update_plants(self):
        for plant in self.plant_sprites.sprites():
            plant.grow()

    def create_soil_tiles(self):
        self.soil_sprites.empty()

        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                if 'X' in cell:
                    t = 'X' in self.grid[index_row - 1][index_col]
                    b = 'X' in self.grid[index_row + 1][index_col]
                    r = 'X' in row[index_col + 1]
                    l = 'X' in row[index_col - 1]

                    tile_type = 'o'

                    # soil patches on all sides
                    if all((t, b, r, l)):
                        tile_type = 'x'

                    # soil patch on the left side
                    if l and not any((t, r, b)):
                        tile_type = 'r'

                    # soil patch on the right side
                    if r and not any((t, l, b)):
                        tile_type = 'l'

                    # soil patches on the both sides
                    if r and l and not any((t, b)):
                        tile_type = 'lr'

                    # soil patch above
                    if t and not any((b, l, r)):
                        tile_type = 'b'

                    # soil patch below
                    if b and not any((t, l, r)):
                        tile_type = 't'

                    # soil patch above and below
                    if t and b and not any((l, r)):
                        tile_type = 'tb'

                    # soil patch below and left side
                    if b and l and not any((t, r)):
                        tile_type = 'tr'

                    # soil patch obove and left side
                    if t and l and not any((b, r)):
                        tile_type = 'br'

                    # soil patch below and right side
                    if b and r and not any((t, l)):
                        tile_type = 'tl'

                    # soil patch above and right side
                    if t and r and not any((b, l)):
                        tile_type = 'bl'

                    # soil patch top, bottom, and right
                    if all((t, b, r)) and not l:
                        tile_type = 'tbr'

                    # soil patch top, bottom, and left
                    if all((t, b, l)) and not r:
                        tile_type = 'tbl'

                    # soil patch top, right, and left
                    if all((t, r, l)) and not b:
                        tile_type = 'lrb'

                    # soil patch bottom, right, and left
                    if all((b, r, l)) and not t:
                        tile_type = 'lrt'

                    SoilTile((index_col * TILE_SIZE, index_row * TILE_SIZE),
                             self.soil_surfaces[tile_type],
                             [self.all_sprites, self.soil_sprites])
