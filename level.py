import pygame
from settings import *
from player import Player
from overlay import Overlay
from sprites import Generic, Water, WildFlower, Tree, Interaction, Particle
from pytmx.util_pygame import load_pygame
from support import *
from debug import draw_hitboxes
from transition import Transition
from soil import SoilLayer
from sky import Rain, Sky
from random import randint
from menu import Menu


class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()

        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.tree_sprites = pygame.sprite.Group()
        self.interaction_sprites = pygame.sprite.Group()

        self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)
        self.setup()
        self.overlay = Overlay(self.player)
        self.transition = Transition(self.reset, self.player)

        self.rain = Rain(self.all_sprites)
        self.raining = randint(0, 10) > 6
        self.soil_layer.raining = self.raining
        self.sky = Sky()

        self.menu = Menu(self.player, self.toggle_shop)
        self.shop_active = False

        self.success = pygame.mixer.Sound('audio/success.wav')
        self.success.set_volume(0.4)

    def setup(self):
        tmx_data = load_pygame('graphics/map.tmx')

        for layer in ['HouseFloor', 'HouseFurnitureBottom']:
            for x, y, surface in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE, y*TILE_SIZE),
                        surface,
                        self.all_sprites,
                        LAYERS['house bottom'])

        for layer in ['HouseWalls', 'HouseFurnitureTop']:
            for x, y, surface in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE, y*TILE_SIZE),
                        surface,
                        self.all_sprites)

        for x, y, surface in tmx_data.get_layer_by_name('Fence').tiles():
            Generic((x*TILE_SIZE, y*TILE_SIZE),
                    surface,
                    [self.all_sprites, self.collision_sprites])

        water_frames = import_folder('graphics/water')
        for x, y, surface in tmx_data.get_layer_by_name('Water').tiles():
            Water((x*TILE_SIZE, y*TILE_SIZE),
                  water_frames,
                  self.all_sprites)

        for obj in tmx_data.get_layer_by_name('Decoration'):
            WildFlower((obj.x, obj.y), obj.image, [
                       self.all_sprites, self.collision_sprites])

        for obj in tmx_data.get_layer_by_name('Trees'):
            Tree((obj.x, obj.y),
                 obj.image,
                 [self.all_sprites, self.collision_sprites, self.tree_sprites],
                 obj.name,
                 add_inventory=self.add_inventory)

        Generic((0, 0),
                pygame.image.load('graphics/world/ground.png').convert_alpha(),
                self.all_sprites,
                LAYERS['ground'])

        for x, y, surface in tmx_data.get_layer_by_name('Collision').tiles():
            Generic((x*TILE_SIZE, y*TILE_SIZE),
                    pygame.Surface((TILE_SIZE, TILE_SIZE)),
                    self.collision_sprites)

        for obj in tmx_data.get_layer_by_name('Player'):
            if obj.name == 'Start':
                self.player = Player((obj.x, obj.y),
                                     self.all_sprites,
                                     self.collision_sprites,
                                     self.tree_sprites,
                                     self.interaction_sprites,
                                     self.soil_layer,
                                     self.toggle_shop)

            if obj.name == 'Bed':
                Interaction((obj.x, obj.y),
                            (obj.width, obj.height),
                            self.interaction_sprites,
                            obj.name)

            if obj.name == 'Trader':
                Interaction((obj.x, obj.y),
                            (obj.width, obj.height),
                            self.interaction_sprites,
                            obj.name)

    def add_inventory(self, item, count=1):
        self.player.item_inventory[item] += count
        pygame.mixer.stop()
        self.success.play()
        print(self.player.item_inventory)

    def toggle_shop(self):
        self.shop_active = not self.shop_active

    def reset(self):
        self.soil_layer.update_plants()

        for tree in self.tree_sprites.sprites():
            for apple in tree.apple_sprites.sprites():
                apple.kill()

            tree.create_fruit()

        self.soil_layer.remove_water()
        self.soil_layer.raining = self.raining

        if self.raining:
            self.soil_layer.water_all()

        self.sky.start_color = [255, 255, 255]

    def plant_collision(self):
        if self.soil_layer.plant_sprites:
            for plant in self.soil_layer.plant_sprites.sprites():
                if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
                    plant.kill()
                    self.soil_layer.grid[plant.rect.centery //
                                         TILE_SIZE][plant.rect.centerx // TILE_SIZE].remove('P')

                    if not plant.plant_dead:
                        self.add_inventory(plant.plant_type)
                        Particle(plant.rect.topleft,
                                 plant.image,
                                 self.all_sprites,
                                 LAYERS['main'])

    def run(self, dt):
        self.display_surface.fill("black")
        self.all_sprites.custom_draw(self.player)

        if self.shop_active:
            self.menu.update()
        else:
            self.all_sprites.update(dt)
            self.plant_collision()

        self.overlay.display()

        if self.raining and not self.shop_active:
            self.rain.update()

        self.sky.display(dt)

        if self.player.sleep:
            self.transition.play()


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()

        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
        self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2

        for layer in LAYERS.values():
            for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
                if sprite.z == layer:
                    offset_rect = sprite.rect.copy()
                    offset_rect.center -= self.offset
                    self.display_surface.blit(sprite.image, offset_rect)

                    # debug, turn on hitboxes
                    # if sprite == player:
                    #     draw_hitboxes(self, player, offset_rect)
