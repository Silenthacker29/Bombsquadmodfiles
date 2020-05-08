#Made by Froshlee14
#Thanks to Mikirog!!!
import bs
import bsSpaz
import random
import bsUtils
import bsBomb
import bsVector
from bsSpaz import _BombDiedMessage

def bsGetAPIVersion():
    return 4

def bsGetGames():
    return [DeathMatchGame]

class PlayerSpazTeleporter(bs.PlayerSpaz):
    def onJumpPress(self):
        """
        Called to 'press jump' on this spaz;
        used for player or AI connections.
        """
        if not self.node.exists() or self.frozen or self.node.knockout > 0.0: return        
        if self.punchCallback is not None:
            self.punchCallback(self)
        t = bs.getGameTime()
        self._punchedNodes = set() # reset this..
        if (t - self.lastPunchTime)/0.3 > self._punchCooldown:
            self.lastPunchTime = t
            self.node.punchPressed = True
            self.landMineCount = 1
            if not self.node.holdNode.exists():
                bs.gameTimer(1,bs.WeakCall(self._safePlaySound,self.getFactory().swishSound,0.8))

class PlayerSpazJumper(bs.PlayerSpaz):
    def onJumpPress(self):
        """
        Called to 'press jump' on this spaz;
        used by player or AI connections.
        """
        if not self.node.exists(): return
        self.node.jumpPressed = True
        self.landMineCount=2

class PlayerSpazBomber(bs.PlayerSpaz):
	def handleMessage(self, m):
		if isinstance(m, _BombDiedMessage):
			#bs.screenMessage('recyceling')
			self.bombCount += 1
		else:
			super(self.__class__, self).handleMessage(m)

	def dropBomb(self):
		if (self.bombCount <= 0) or self.frozen:
			return
		p = self.node.positionForward
		v = self.node.velocity
		bomb = bs.Bomb(position=(p[0], p[1] - 0.0, p[2]),
					   velocity=(v[0], v[1], v[2]),
					   bombType=self.bombType,
					   blastRadius=6,
					   sourcePlayer=self.sourcePlayer,
					   owner=self.node).autoRetain()
		bsUtils.animate(bomb.node, 'modelScale', {0:1.0, 3000:1.7},loop = False)
		self.bombCount -= 1
		bomb.node.addDeathAction(bs.WeakCall(self.handleMessage, _BombDiedMessage()))
		self._pickUp(bomb.node)
		for meth in self._droppedBombCallbacks:
			meth(self, bomb)
		return bomb

class PlayerSpazNormal(bs.PlayerSpaz):
    def equipSpeed(self):
        """
        Give this spaz speed boots.
        """
        factory = self.getFactory()
        def _safeSetAttr(node,attr,val):
            if node.exists(): setattr(node,attr,val)
        bs.gameTimer(1,bs.Call(_safeSetAttr,self.node,'hockey',True))

    def equipShields(self, decay=False):
        """
        Give this spaz a nice energy shield.
        """
        if not self.node.exists():
            bs.printError('Can\'t equip shields; no node.')
            return        
        factory = self.getFactory()
        if self.shield is None: 
            self.shield = bs.newNode('shield',owner=self.node,
                                     attrs={'color':(1.5,0,0),'radius':1.3})
            self.node.connectAttr('positionCenter',self.shield,'position')
        self.shieldHitPoints = self.shieldHitPointsMax = 6000
        #self.shieldDecayRate = factory.shieldDecayRate if decay else 0
        self.shield.hurt = 0
        bs.playSound(factory.shieldUpSound,1.0,position=self.node.position)
        #if self.shieldDecayRate > 0:
       #     self.shieldDecayTimer = bs.Timer(500,bs.WeakCall(self.shieldDecay),repeat=True)
        #    self.shield.alwaysShowHealthBar = True # so the user can see the decay

class PlayerSpazFrozenman(bs.PlayerSpaz):
    def onPunchPress(self):
        """
        Called to 'press punch' on this spaz;
        used for player or AI connections.
        """
        if not self.node.exists() or self.frozen or self.node.knockout > 0.0: return
        if self.punchCallback is not None:
            self.punchCallback(self)
        t = bs.getGameTime()
        self._punchedNodes = set() # reset this..
        if (t - self.lastPunchTime)/105 > self._punchCooldown:
            self.lastPunchTime = t
            self.node.punchPressed = True
            self.landMineCount=3
            if not self.node.holdNode.exists():
                bs.gameTimer(100,bs.WeakCall(self._safePlaySound,self.getFactory().swishSound,0.8))				

class DeathMatchGame(bs.TeamGameActivity):

    @classmethod
    def getName(cls):
        return 'Super Fighter'

    @classmethod
    def getDescription(cls,sessionType):
        return ('Powers available: \n-Teleporter: Punch to teleport yourself\n-Jumper: Press jump to "fly" \n-Bomber: Drop mega bombs \n-Stronger: He is super strong \n-Speedman: Run real fast! \n-Frozenman: Punch to frozen everybody\n-Shieldman: Has a super shield\n\nIf you die, maybe change your powers')

    @classmethod
    def supportsSessionType(cls,sessionType):
        return True if (issubclass(sessionType,bs.TeamsSession)
                        or issubclass(sessionType,bs.FreeForAllSession)) else False

    @classmethod
    def getSupportedMaps(cls,sessionType):
        return bs.getMapsSupportingPlayType("melee")

    @classmethod
    def getSettings(cls,sessionType):
        return [("KOs to Win Per Player",{'minValue':1,'default':5,'increment':1}),
                ("Time Limit",{'choices':[('None',0),('1 Minute',60),
                                        ('2 Minutes',120),('5 Minutes',300),
                                        ('10 Minutes',600),('20 Minutes',1200)],'default':0}),
                ("Respawn Times",{'choices':[('Shorter',0.25),('Short',0.5),('Normal',1.0),('Long',2.0),('Longer',4.0)],'default':1.0}),
                ("Epic Mode",{'default':False})]


    def __init__(self,settings):
        bs.TeamGameActivity.__init__(self,settings)
        if self.settings['Epic Mode']: self._isSlowMotion = True

        # print messages when players die since it matters here..
        self.announcePlayerDeaths = True
        
        self._scoreBoard = bs.ScoreBoard()

    def getInstanceDescription(self):
        return ('KO ${ARG1} of your enemies.',self._scoreToWin)

    def getInstanceScoreBoardDescription(self):
        return ('KO ${ARG1} enemies',self._scoreToWin)

    def onTransitionIn(self):
        bs.TeamGameActivity.onTransitionIn(self, music='Epic' if self.settings['Epic Mode'] else 'GrandRomp')

    def onTeamJoin(self,team):
        team.gameData['score'] = 0
        if self.hasBegun(): self._updateScoreBoard()

    def onBegin(self):
        bs.TeamGameActivity.onBegin(self)
        self.setupStandardTimeLimit(self.settings['Time Limit'])
        #self.setupStandardPowerupDrops()
        if len(self.teams) > 0:
            self._scoreToWin = self.settings['KOs to Win Per Player'] * max(1,max(len(t.players) for t in self.teams))
        else: self._scoreToWin = self.settings['KOs to Win Per Player']
        self._updateScoreBoard()
        self._dingSound = bs.getSound('dingSmall')
        bs.gameTimer(100,bs.WeakCall(self.givePowers),repeat=True)

    def givePowers(self):
        for player in self.players:
         if not player.actor is None:
          if player.actor.isAlive():
           #This teleport the player
           if player.actor.landMineCount==1:
            pos = self.getMap().getFFAStartPosition(self.players)
            player.actor.handleMessage(bs.StandMessage(pos))
            bs.Blast(position=pos,blastRadius=1.0,blastType='smoke').autoRetain()
            bs.playSound(bs.getSound('shieldDown'))
            player.actor.landMineCount=0
           #The player will be fly with the explosions
           elif player.actor.landMineCount==2:
            pos = player.actor.node.position
            bs.Blast(position=(pos[0],pos[1]-0.5,pos[2]),blastRadius=1.0,blastType='smoke').autoRetain()
            player.actor.handleMessage(bs.PowerupMessage('health'))
            player.actor.landMineCount=0
           elif player.actor.landMineCount==3:
            mPlayer = player.actor
            self.freezeAll(mPlayer)
            player.actor.landMineCount=0

    #Magic affect everybody except the Frozenman
    def freezeAll(self,mPlayer):
        for player in self.players:
         if not player.actor is mPlayer:
          if player.actor.isAlive():
           if player.actor.node.frozen == True:      
            player.actor.node.frozen = False
           else:
            player.actor.node.frozen = True
            bs.playSound(bs.getSound('freeze'))

    def spawnPlayerSpaz(self,player,position=(0,0,0),angle=None):
        """
        Create and wire up a bs.PlayerSpaz for the provide bs.Player.
        """
        position = self.getMap().getFFAStartPosition(self.players)
        name = player.getName()
        color = player.color
        highlight = player.highlight

        lightColor = bsUtils.getNormalizedColor(color)
        displayColor = bs.getSafeColor(color,targetIntensity=0.75)

        bt =random.choice(['Jumper','Hopper','Bomber','Stronger','Flash','Frozenman','Shieldman'])
        if bt == 'Jumper':
         bt = PlayerSpazTeleporter
         name += '\nJUMPER'
        elif bt == 'Hopper':
         bt = PlayerSpazJumper
         name += '\nHOPPER'
        elif bt == 'Bomber':
         bt = PlayerSpazBomber
         name += '\nBOMBER'
        elif bt == 'Stronger':
         extra = 'strong'
         bt = PlayerSpazNormal
         name += '\nHULK'
        elif bt == 'Flash':
         extra = 'speed'
         bt = PlayerSpazNormal
         name += '\nFLASH'
        elif bt == 'Frozenman':
         bt = PlayerSpazFrozenman
         name += '\nICEMAN'
        elif bt == 'Shieldman':
         extra = 'shield'
         bt = PlayerSpazNormal
         name += '\nSHIELDMAN'

        s = spaz = bt(color=color,
                              highlight=highlight,
                              character=player.character,
                              player=player)
        if bt==PlayerSpazFrozenman: spaz.bombType = 'ice'
        if bt==PlayerSpazNormal and extra=='speed': spaz.equipSpeed()
        if bt==PlayerSpazNormal and extra=='shield': spaz.equipShields()
        if bt==PlayerSpazNormal and extra=='strong': s._punchPowerScale = 5
        player.setActor(spaz)
                         
        spaz.node.name = name
        spaz.node.nameColor = displayColor
        spaz.connectControlsToPlayer()
                
        self.scoreSet.playerGotNewSpaz(player,spaz)

        # move to the stand position and add a flash of light
        spaz.handleMessage(bs.StandMessage(position,angle if angle is not None else random.uniform(0,360)))
        t = bs.getGameTime()
        bs.playSound(self._spawnSound,1,position=spaz.node.position)
        light = bs.newNode('light',attrs={'color':lightColor})
        spaz.node.connectAttr('position',light,'position')
        bsUtils.animate(light,'intensity',{0:0,250:1,500:0})
        bs.gameTimer(500,light.delete)
        return spaz

    def handleMessage(self,m):

        if isinstance(m,bs.PlayerSpazDeathMessage):
            bs.TeamGameActivity.handleMessage(self,m) # augment standard behavior

            player = m.spaz.getPlayer()
            self.respawnPlayer(player)

            killer = m.killerPlayer
            if killer is None: return

            # handle team-kills
            if killer.getTeam() is player.getTeam():

                # in free-for-all, killing yourself loses you a point
                if isinstance(self.getSession(),bs.FreeForAllSession):
                    player.getTeam().gameData['score'] = max(0,player.getTeam().gameData['score']-1)

                # in teams-mode it gives a point to the other team
                else:
                    bs.playSound(self._dingSound)
                    for team in self.teams:
                        if team is not killer.getTeam():
                            team.gameData['score'] += 1

            # killing someone on another team nets a kill
            else:
                killer.getTeam().gameData['score'] += 1
                bs.playSound(self._dingSound)
                # in FFA show our score since its hard to find on the scoreboard
                try: killer.actor.setScoreText(str(killer.getTeam().gameData['score'])+'/'+str(self._scoreToWin),color=killer.getTeam().color,flash=True)
                except Exception: pass

            self._updateScoreBoard()

            # if someone has won, set a timer to end shortly
            # (allows the dust to clear and draws to occur if deaths are close enough)
            if any(team.gameData['score'] >= self._scoreToWin for team in self.teams):
                bs.gameTimer(500,self.endGame)

        else: bs.TeamGameActivity.handleMessage(self,m)

    def _updateScoreBoard(self):
        for team in self.teams:
            self._scoreBoard.setTeamValue(team,team.gameData['score'],self._scoreToWin)

    def endGame(self):
        results = bs.TeamGameResults()
        for t in self.teams: results.setTeamScore(t,t.gameData['score'])
        self.end(results=results)
