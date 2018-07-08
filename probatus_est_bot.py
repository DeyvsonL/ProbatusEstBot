import random
import asyncio
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human
import time
from sc2.position import Point2

scout_tags = []
enemy_position = 0
qtd_marines = 50
qtd_hellion = 15
qtd_medivac = 7 
qtd_cyclone = 27

class Agent:
    async def on_step(self, bot, iteration):
        raise NotImplementedError

class Scouter(Agent):
    def isScout(self, bot, scv):
        if(bot.units(SCV).find_by_tag(scv.tag)==None):
            return False
        else:
            return True

    def add_scout(self, bot):
        global scout_tags
        w = bot.units(SCV)
        if w.exists:
            w_aux = w.random
            scout_tags.append(w_aux.tag)
            return w_aux
        return None
        

    def update_scout_tags(self, bot):
        global scout_tags
        scout_tags_aux = []
        for tag in scout_tags:
            if(bot.units(SCV).find_by_tag(tag)!=None):
                scout_tags_aux.append(tag)
        scout_tags = scout_tags_aux

    def check_len_scout(self, bot):
        if(len(scout_tags)<6):
            w = self.add_scout(bot)
            if(w!=None):
                scout_tags.append(w.tag)
        
    """def get_position_send_scout(self, bot):
        count = 0
        for tag in scout_tags:
            position = bot.enemy_start_locations[count%len(bot.enemy_start_locations)]
            worker = bot.units(SCV).find_by_tag(tag)
            if(worker!=None):
                loop = asyncio.get_event_loop()
                await bot.do(worker.stop())
            count=count+1"""
           

    async def on_step(self, bot, iteration):
        if(iteration==0 or iteration%200==0):
            global scout_tags
            loop = asyncio.get_event_loop()
            units = bot.units(SCV)
            await loop.run_in_executor(None, self.update_scout_tags, bot)
            await loop.run_in_executor(None, self.check_len_scout, bot)
            target = bot.known_enemy_structures
            #await loop.run_in_executor(None, self.send_scout, bot)
            enemy_start_locations = bot.enemy_start_locations
            units = bot.units(SCV)
            position = enemy_start_locations[0]
            for tag in scout_tags:
                worker = units.find_by_tag(tag)
                if(worker!=None):
                    await bot.do(worker.move(position))
            #self.send_scout(bot)

class Command(Agent):        

    async def on_step(self, bot, iteration):
        cc = bot.units(COMMANDCENTER)
        if not cc.exists:
            target = bot.known_enemy_structures.random_or(bot.enemy_start_locations[0]).position
            for unit in bot.workers | bot.units(HELLIONTANK):
                await bot.do(unit.attack(target))
            return
        else:
            cc = cc.random

        if(iteration==0 or iteration%20==0):
            if bot.can_afford(SCV) and bot.workers.amount < 25 and cc.noqueue:
                await bot.do(cc.train(SCV))
            elif bot.supply_left < 3:
                if bot.can_afford(SUPPLYDEPOT) and bot.already_pending(SUPPLYDEPOT) < 2:
                    await bot.build(SUPPLYDEPOT, near=cc.position.towards(bot.game_info.map_center, 8))

            if bot.units(SUPPLYDEPOT).exists:
                if not bot.units(BARRACKS).exists:
                    if bot.can_afford(BARRACKS):
                        await bot.build(BARRACKS, near=cc.position.towards(bot.game_info.map_center, 8))

                elif bot.units(BARRACKS).exists and bot.units(REFINERY).amount < 2:
                    if bot.can_afford(REFINERY):
                        vgs = bot.state.vespene_geyser.closer_than(20.0, cc)
                        for vg in vgs:
                            if bot.units(REFINERY).closer_than(1.0, vg).exists:
                                break

                            worker = bot.select_build_worker(vg.position)
                            if worker is None:
                                break

                            await bot.do(worker.build(REFINERY, vg))
                            break

                if bot.units(BARRACKS).ready.exists:
                    if bot.units(FACTORY).amount < 3 and not bot.already_pending(HELLIONTANK):
                        if bot.can_afford(FACTORY):
                            p = cc.position.towards_with_random_angle(bot.game_info.map_center, 16)
                            await bot.build(FACTORY, near=p)
                    if bot.units(FACTORY).ready.exists:
                        if bot.can_afford(ARMORY) and not bot.units(ARMORY).exists:
                            p = cc.position.towards_with_random_angle(bot.game_info.map_center, 16)
                            await bot.build(ARMORY, near=p)
                        if bot.units(ARMORY).ready.exists:
                            if bot.can_afford(STARPORT) and not bot.units(STARPORT).exists:
                                p = cc.position.towards_with_random_angle(bot.game_info.map_center, 16)
                                await bot.build(STARPORT, near=p)

        for barrack in bot.units(BARRACKS).ready.noqueue:
                # Reactor allows us to build two at a time
            if bot.can_afford(MARINE) and bot.units(MARINE).amount < qtd_marines:
                await bot.do(barrack.train(MARINE))

            for factory in bot.units(FACTORY).ready.noqueue:
                if bot.can_afford(CYCLONE) and bot.units(CYCLONE).amount < qtd_cyclone:
                        await bot.do(factory.train(CYCLONE)) 
                elif bot.units(ARMORY).exists:
                    # if factory.has_add_on == 0:
                    #     await self.do(factory.build(FACTORYTECHLAB))
                    # elif self.can_afford(THOR) and self.units(THOR).amount < self.qtd_thor:
                    #     await self.do(factory.train(THOR))
                    if bot.can_afford(HELLIONTANK) and bot.units(HELLIONTANK).amount < qtd_hellion:
                        await bot.do(factory.train(HELLIONTANK))

            for starport in bot.units(STARPORT).ready.noqueue:
                # Reactor allows us to build two at a time
                if bot.can_afford(MEDIVAC) and bot.units(MEDIVAC).amount < qtd_medivac:
                    await bot.do(starport.train(MEDIVAC))

        for a in bot.units(REFINERY):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = bot.workers.closer_than(20, a)
                if w.exists:
                    await bot.do(w.random.gather(a))

        for scv in bot.units(SCV).idle:
            await bot.do(scv.gather(bot.state.mineral_field.closest_to(cc)))

            

class ProbatusEstBot(sc2.BotAI):
    def __init__(self):
        self._agents = []
 
    def on_start(self):
        self._agents.append(Scouter())
        self._agents.append(Command())

    
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
        loop = asyncio.get_event_loop()
        tasks = []
        for agent in self._agents:
            tasks.append(loop.create_task(agent.on_step(self, iteration)))
        done, pending = await asyncio.wait(tasks, timeout=200.0)
        for task in pending:
            task.cancel()

        self.select_target


        
        depos = [
            Point2((max({p.x for p in d}), min({p.y for p in d})))
            for d in self.main_base_ramp.top_wall_depos
        ]

       
            
#fechar a base (construir bunker)
        
        depo_count = (self.units(BUNKER)).amount
        if self.can_afford(BUNKER) and not self.already_pending(BUNKER):
            if depo_count >= len(depos):
                return
            depo = list(depos)[depo_count]
            r = await self.build(BUNKER, near=depo, max_distance=2)

        
        # if self.can_afford(BUNKER) and self.units(BUNKER).amount < 3:
        #     if self.enemy_position == 0:
        #         await self.build(BUNKER, near=cc.position.towards(self.game_info.map_center, 50))
        #     else:
        #         await self.build(BUNKER, near=cc.position.towards(self.enemy_position, 50))

#attack
        if iteration % 50 == 0 and (self.units(HELLIONTANK).amount > 2 and self.units(MARINE).amount > 20):
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
            forces = self.units(CYCLONE)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target)) 
                       
        #build
        depos = [
            Point2((max({p.x for p in d}), min({p.y for p in d})))
            for d in self.main_base_ramp.top_wall_depos
        ]
        depo_count = (self.units(SUPPLYDEPOT)).amount

        if self.can_afford(SUPPLYDEPOT) and self.units(SUPPLYDEPOT).amount < 2:
            depo = list(depos)[depo_count]
            await self.build(SUPPLYDEPOT, near=depo)



        


def main():
    sc2.run_game(sc2.maps.get("Sequencer LE"), [
        # Human(Race.Terran),
        Bot(Race.Terran, ProbatusEstBot()),
        Computer(Race.Zerg, Difficulty.Hard)
    ], realtime=False)


if __name__ == '__main__':
    main()