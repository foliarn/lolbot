"""
Module Training Exercises - Exercices per-game bases sur les timelines
"""
import operator
import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

import discord

import config

PARIS_TZ = ZoneInfo("Europe/Paris")

# Operator mapping for condition evaluation
OPS = {
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '<=': operator.le,
    '>': operator.gt,
    '<': operator.lt,
}


class TrainingExercises:
    """Gestion des exercices d'entrainement bases sur les timelines de match"""

    def __init__(self, riot_api, db_manager, bot):
        self.api = riot_api
        self.db = db_manager
        self.bot = bot

    # ==================== Timeline Stat Extractors ====================

    def _get_frame_at_time(self, frames: List[Dict], time_ms: int) -> Optional[Dict]:
        """Retourne la frame la plus proche avant time_ms"""
        target_frame = None
        for frame in frames:
            if frame.get('timestamp', 0) <= time_ms:
                target_frame = frame
            else:
                break
        return target_frame

    def _get_participant_frame(self, frame: Dict, participant_id: int) -> Optional[Dict]:
        """Extrait les donnees d'un participant depuis une frame"""
        if not frame or 'participantFrames' not in frame:
            return None
        return frame['participantFrames'].get(str(participant_id))

    def _get_events_before_time(self, frames: List[Dict], time_ms: int) -> List[Dict]:
        """Recupere tous les evenements avant un timestamp"""
        events = []
        for frame in frames:
            for event in frame.get('events', []):
                if event.get('timestamp', 0) <= time_ms:
                    events.append(event)
        return events

    def deaths_before_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Compte les morts du joueur avant un timestamp"""
        events = self._get_events_before_time(frames, time_ms)
        return sum(
            1 for e in events
            if e.get('type') == 'CHAMPION_KILL' and e.get('victimId') == participant_id
        )

    def kills_before_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Compte les kills du joueur avant un timestamp"""
        events = self._get_events_before_time(frames, time_ms)
        return sum(
            1 for e in events
            if e.get('type') == 'CHAMPION_KILL' and e.get('killerId') == participant_id
        )

    def total_cs_at_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """CS total (minions + jungle) a un timestamp"""
        frame = self._get_frame_at_time(frames, time_ms)
        pf = self._get_participant_frame(frame, participant_id)
        if not pf:
            return 0
        return pf.get('minionsKilled', 0) + pf.get('jungleMinionsKilled', 0)

    def damage_to_champions_at_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Degats aux champions a un timestamp"""
        frame = self._get_frame_at_time(frames, time_ms)
        pf = self._get_participant_frame(frame, participant_id)
        if not pf:
            return 0
        damage_stats = pf.get('damageStats', {})
        return damage_stats.get('totalDamageDoneToChampions', 0)

    def gold_at_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Gold total a un timestamp"""
        frame = self._get_frame_at_time(frames, time_ms)
        pf = self._get_participant_frame(frame, participant_id)
        if not pf:
            return 0
        return pf.get('totalGold', 0)

    def gold_advantage_at_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Avantage de gold par rapport a la moyenne ennemie a un timestamp"""
        frame = self._get_frame_at_time(frames, time_ms)
        if not frame or 'participantFrames' not in frame:
            return 0

        pf = self._get_participant_frame(frame, participant_id)
        if not pf:
            return 0

        player_gold = pf.get('totalGold', 0)
        # Determine enemy team (participants 1-5 vs 6-10)
        is_team_one = participant_id <= 5
        enemy_golds = []
        for pid_str, data in frame['participantFrames'].items():
            pid = int(pid_str)
            if is_team_one and pid > 5:
                enemy_golds.append(data.get('totalGold', 0))
            elif not is_team_one and pid <= 5:
                enemy_golds.append(data.get('totalGold', 0))

        if not enemy_golds:
            return 0
        enemy_avg = sum(enemy_golds) / len(enemy_golds)
        return int(player_gold - enemy_avg)

    def level_at_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Niveau du joueur a un timestamp"""
        frame = self._get_frame_at_time(frames, time_ms)
        pf = self._get_participant_frame(frame, participant_id)
        if not pf:
            return 0
        return pf.get('level', 0)

    def wards_placed_before_time(self, frames: List[Dict], participant_id: int, time_ms: int) -> int:
        """Compte les wards posees avant un timestamp"""
        events = self._get_events_before_time(frames, time_ms)
        return sum(
            1 for e in events
            if e.get('type') == 'WARD_PLACED' and e.get('creatorId') == participant_id
        )

    # ==================== Condition Evaluation ====================

    def _evaluate_condition(self, condition: Dict, frames: List[Dict], participant_id: int) -> bool:
        """Evalue une condition d'exercice contre les donnees de timeline"""
        stat_name = condition['stat']
        op_str = condition['op']
        target_value = condition['value']
        time_ms = condition.get('time_ms')

        # Get the stat extractor method
        extractor = getattr(self, stat_name, None)
        if not extractor:
            print(f"[Exercises] Extracteur inconnu: {stat_name}")
            return False

        actual_value = extractor(frames, participant_id, time_ms)
        op_func = OPS.get(op_str)
        if not op_func:
            print(f"[Exercises] Operateur inconnu: {op_str}")
            return False

        return op_func(actual_value, target_value)

    def _evaluate_exercise(self, exercise: Dict, frames: List[Dict], participant_id: int) -> bool:
        """Evalue toutes les conditions d'un exercice (AND logic)"""
        conditions = exercise.get('conditions', [])
        if not conditions:
            return False

        return all(
            self._evaluate_condition(cond, frames, participant_id)
            for cond in conditions
        )

    # ==================== Match Processing ====================

    def _find_participant_id(self, match_data: Dict, puuid: str) -> Optional[int]:
        """Trouve le participantId d'un joueur dans un match"""
        participants = match_data.get('info', {}).get('participants', [])
        for p in participants:
            if p.get('puuid') == puuid:
                return p.get('participantId')
        return None

    async def check_all_players(self):
        """Verifie les exercices pour tous les joueurs ayant des exercices actives"""
        puuids = await self.db.get_all_exercise_users()
        if not puuids:
            return

        for puuid in puuids:
            try:
                await self._process_player(puuid)
            except Exception as e:
                print(f"[Exercises] Erreur pour {puuid}: {e}")
                traceback.print_exc()

    async def _process_player(self, riot_puuid: str):
        """Traite les exercices d'un joueur"""
        enabled = await self.db.get_enabled_exercises(riot_puuid)
        if not enabled:
            return

        # Find the oldest last_match_id cursor across all exercises
        # (to minimize API calls, process from the earliest unprocessed point)
        last_match_ids = {}
        oldest_cursor = None  # None means never processed
        has_null_cursor = False

        for ex in enabled:
            ex_id = ex['exercise_id']
            lm = ex.get('last_match_id')
            last_match_ids[ex_id] = lm
            if lm is None:
                has_null_cursor = True

        # Fetch recent ranked matches
        season_start_ts = int(
            datetime.strptime(config.SEASON_START_DATE, '%Y-%m-%d')
            .replace(tzinfo=PARIS_TZ)
            .timestamp()
        )

        all_match_ids = []
        page_start = 0
        while True:
            batch = await self.api.get_match_history(
                puuid=riot_puuid,
                start=page_start,
                count=100,
                queue=420,
                start_time=season_start_ts
            )
            if not batch:
                break
            all_match_ids.extend(batch)
            if len(batch) < 100:
                break
            page_start += 100

        if not all_match_ids:
            return

        # For each exercise, find which matches are new
        for ex in enabled:
            ex_id = ex['exercise_id']
            exercise_def = config.TRAINING_EXERCISES.get(ex_id)
            if not exercise_def:
                continue

            cursor = last_match_ids.get(ex_id)

            # Find new matches after cursor
            new_match_ids = []
            for match_id in all_match_ids:
                if match_id == cursor:
                    break
                new_match_ids.append(match_id)

            if not new_match_ids:
                # No new matches, but if cursor is None, set it to latest
                if cursor is None and all_match_ids:
                    await self.db.update_exercise_last_match(riot_puuid, ex_id, all_match_ids[0])
                continue

            # Process oldest first
            new_match_ids.reverse()

            for match_id in new_match_ids:
                try:
                    match_data = await self.api.get_match(match_id)
                    if not match_data:
                        continue

                    timeline_data = await self.api.get_match_timeline(match_id)
                    if not timeline_data:
                        continue

                    participant_id = self._find_participant_id(match_data, riot_puuid)
                    if not participant_id:
                        continue

                    frames = timeline_data.get('info', {}).get('frames', [])
                    if not frames:
                        continue

                    # Check if match was long enough for the exercise conditions
                    match_duration_ms = match_data.get('info', {}).get('gameDuration', 0) * 1000
                    max_time = max(c.get('time_ms', 0) for c in exercise_def.get('conditions', []))
                    if match_duration_ms < max_time:
                        # Game ended before the exercise time window - skip
                        continue

                    success = self._evaluate_exercise(exercise_def, frames, participant_id)
                    match_timestamp = match_data.get('info', {}).get('gameCreation', 0)

                    await self.db.record_exercise_attempt(
                        riot_puuid, ex_id, match_id, success, match_timestamp
                    )
                except Exception as e:
                    print(f"[Exercises] Erreur match {match_id}: {e}")
                    traceback.print_exc()

            # Update cursor to latest match
            await self.db.update_exercise_last_match(riot_puuid, ex_id, all_match_ids[0])

    # ==================== Embed Generators ====================

    def generate_exercise_list_embed(self) -> discord.Embed:
        """Genere un embed listant tous les exercices disponibles"""
        embed = discord.Embed(
            title="Exercices d'Entrainement",
            description="Exercices per-game evalues sur les timelines de match.\nUtilisez `/exercises enable <id>` pour activer le tracking.",
            color=discord.Color.blue()
        )

        for ex_id, ex in config.TRAINING_EXERCISES.items():
            embed.add_field(
                name=f"{ex['name']} (`{ex_id}`)",
                value=ex['description'],
                inline=False
            )

        return embed

    async def generate_exercise_stats_embed(self, discord_id: str) -> discord.Embed:
        """Genere un embed avec les stats d'exercices d'un joueur"""
        user = await self.db.get_user(discord_id)
        if not user:
            embed = discord.Embed(
                title="Exercices",
                description="Aucun compte lie. Utilisez `/link` d'abord.",
                color=discord.Color.red()
            )
            return embed

        riot_puuid = user['riot_puuid']
        enabled = await self.db.get_enabled_exercises(riot_puuid)
        all_stats = await self.db.get_all_exercise_stats(riot_puuid)

        embed = discord.Embed(
            title="Mes Exercices",
            description=f"**{user['game_name']}#{user['tag_line']}**",
            color=discord.Color.green()
        )

        if not enabled:
            embed.description += "\n\nAucun exercice active. Utilisez `/exercises enable <id>`."
            return embed

        for ex in enabled:
            ex_id = ex['exercise_id']
            exercise_def = config.TRAINING_EXERCISES.get(ex_id)
            if not exercise_def:
                continue

            stats = all_stats.get(ex_id, {'total': 0, 'success': 0})
            total = stats['total']
            success = stats['success']
            pct = (success / total * 100) if total > 0 else 0

            if total == 0:
                status = "En attente de matchs..."
            else:
                bar_len = 10
                filled = int(pct / 100 * bar_len)
                bar = '█' * filled + '░' * (bar_len - filled)
                status = f"{bar} {success}/{total} ({pct:.0f}%)"

            embed.add_field(
                name=f"{exercise_def['name']}",
                value=f"{exercise_def['description']}\n{status}",
                inline=False
            )

        return embed
