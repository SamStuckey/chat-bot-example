"""The wired services the routes use, built once by the composition root."""

from dataclasses import dataclass

from penny.accounts.service import AccountService
from penny.auth.service import DemoSessionIssuer, TokenVerifier
from penny.conversation.runner import TurnRunner
from penny.conversation.service import ConversationService
from penny.conversation.stop import StopRegistry
from penny.health.service import HealthService


@dataclass(frozen=True)
class Services:
    accounts: AccountService
    conversations: ConversationService
    runner: TurnRunner
    stops: StopRegistry
    verifier: TokenVerifier
    demo_sessions: DemoSessionIssuer
    health: HealthService
