import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human
from sc2.position import Point2

class ProbatusEstBot(sc2.BotAI):
    
    enemy_position = 0
    qtd_marines = 50
    qtd_hellbat = 10
    qtd_thor = 10
    qtd_medivac = 5 
    qtd_viking = 4
    qtd_cyclone = 3
    qtd_battlecruizer = 3

    #Fugir para a base
    def fugir_para_base(unit):
        self.do(unit.move(cc.position.towards(self.units(COMMANDCENTER), 8)))
    
    #Atacar inimigo na base
    def inimigo_na_base():
        for unit in self.workers | self.units(HELLIONTANK):
            await self.do(unit.attack(target))

    #Fugir para a base
    def fugir_para_base(self, unit):
        cc = self.units(COMMANDCENTER)
        self.do(unit.move(cc.position.towards(self.units(COMMANDCENTER), 8)))
    
    #Atacar inimigo na base
    async def inimigo_na_base(self, target):
        for unit in self.workers | self.units(HELLIONTANK):
            await self.do(unit.attack(target))
    
    def select_target(self):
        target = self.known_enemy_structures
        if target.exists:
            return target.random.position

        target = self.known_enemy_units
        if target.exists:
            return target.random.position

        if min([u.position.distance_to(self.enemy_start_locations[0]) for u in self.units]) < 5:
            return self.enemy_start_locations[0].position

        return self.state.mineral_field.random.position
    
    

    async def on_step(self, iteration):
        cc = self.units(COMMANDCENTER)
        
        depos = [
            Point2((max({p.x for p in d}), min({p.y for p in d})))
            for d in self.main_base_ramp.top_wall_depos
        ]

        if not cc.exists:
            target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units(HELLIONTANK):
                await self.do(unit.attack(target))
            return
        else:
            cc = cc.first
            
#fechar a base (construir bunker)
        
        depo_count = (self.units(BUNKER)).amount
        if self.can_afford(BUNKER) and not self.already_pending(BUNKER):
            if depo_count >= len(depos):
                return
            depo = list(depos)[depo_count]
            r = await self.build(BUNKER, near=depo, max_distance=2, placement_step=1)

        
        # if self.can_afford(BUNKER) and self.units(BUNKER).amount < 3:
        #     if self.enemy_position == 0:
        #         await self.build(BUNKER, near=cc.position.towards(self.game_info.map_center, 50))
        #     else:
        #         await self.build(BUNKER, near=cc.position.towards(self.enemy_position, 50))

#attack
        if iteration % 50 == 0 and (self.units(HELLIONTANK).amount > 2 and self.units(MARINE).amount > 10):
            target = self.select_target()
            forces = self.units(HELLIONTANK)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))
            forces = self.units(MARINE)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))
            forces = self.units(MEDIVAC)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))
            forces = self.units(THOR)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))        
#build
        if self.can_afford(SCV) and self.workers.amount < 25 and cc.noqueue:
            await self.do(cc.train(SCV))

        elif self.supply_left < 3:
            if self.can_afford(SUPPLYDEPOT) and self.already_pending(SUPPLYDEPOT) < 2:
                await self.build(SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 8))

        if self.units(SUPPLYDEPOT).exists:
            if not self.units(BARRACKS).exists:
                if self.can_afford(BARRACKS):
                    await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 8))

            elif self.units(BARRACKS).exists and self.units(REFINERY).amount < 2:
                if self.can_afford(REFINERY):
                    vgs = self.state.vespene_geyser.closer_than(20.0, cc)
                    for vg in vgs:
                        if self.units(REFINERY).closer_than(1.0, vg).exists:
                            break

                        worker = self.select_build_worker(vg.position)
                        if worker is None:
                            break

                        await self.do(worker.build(REFINERY, vg))
                        break

            if self.units(BARRACKS).ready.exists:
                if self.units(FACTORY).amount < 3 and not self.already_pending(HELLIONTANK):
                    if self.can_afford(FACTORY):
                        p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                        await self.build(FACTORY, near=p, placement_step=5)
                if self.units(FACTORY).ready.exists:
                    if self.can_afford(ARMORY) and not self.units(ARMORY).exists:
                        p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                        await self.build(ARMORY, near=p, placement_step=5)
                    if self.units(ARMORY).ready.exists:
                        if self.can_afford(STARPORT) and not self.units(STARPORT).exists:
                            p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                            await self.build(STARPORT, near=p, placement_step=5)

        for barrack in self.units(BARRACKS).ready.noqueue:
            # Reactor allows us to build two at a time
            if self.can_afford(MARINE):
                await self.do(barrack.train(MARINE))

        for factory in self.units(FACTORY).ready.noqueue:
            if self.units(ARMORY).exists:
                if factory.has_add_on == 0:
                    await self.do(factory.build(FACTORYTECHLAB))
                elif self.can_afford(THOR):
                    await self.do(factory.train(THOR))
                elif self.can_afford(HELLIONTANK):
                    await self.do(factory.train(HELLIONTANK))

        for starport in self.units(STARPORT).ready.noqueue:
            # Reactor allows us to build two at a time
            if self.can_afford(MEDIVAC) and self.units(MEDIVAC).amount < 6:
                await self.do(starport.train(MEDIVAC))
            elif self.can_afford(VIKING) and self.units(VIKING).amount < 5:    


        for a in self.units(REFINERY):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        for scv in self.units(SCV).idle:
            await self.do(scv.gather(self.state.mineral_field.closest_to(cc)))

def main():
    sc2.run_game(sc2.maps.get("Sequencer LE"), [
        # Human(Race.Terran),
        Bot(Race.Terran, ProbatusEstBot()),
        Computer(Race.Protoss, Difficulty.Hard)
    ], realtime=False)

if __name__ == '__main__':
    main()