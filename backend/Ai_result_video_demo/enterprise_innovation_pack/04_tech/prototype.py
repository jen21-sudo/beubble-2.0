"""
============================================================================
 ENTERPRISE INNOVATION PLATFORM - TECHNICAL PROTOTYPE
 Version: 2.0.0
 Author: Beubble Innovation Lab
 Description: Functional prototype demonstrating an AI-powered enterprise
              innovation management platform that leverages disruptive
              technologies including AI/ML, IoT, 3D Printing integration,
              Sustainability Analytics, and Predictive Mobility.
============================================================================
"""

import json
import uuid
import hashlib
import math
import random
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
import heapq
import statistics

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("InnovationPlatform")


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================
class TechnologyDomain(Enum):
    AI_ML = "ai_ml"
    IOT = "iot"
    THREE_D_PRINTING = "3d_printing"
    SUSTAINABILITY = "sustainability"
    MOBILITY = "mobility"
    BLOCKCHAIN = "blockchain"
    QUANTUM = "quantum_computing"
    BIOTECH = "biotech"
    AR_VR = "ar_vr"
    CYBERSECURITY = "cybersecurity"


class InnovationStage(Enum):
    IDEATION = "ideation"
    RESEARCH = "research"
    PROTOTYPING = "prototyping"
    VALIDATION = "validation"
    SCALING = "scaling"
    DEPLOYMENT = "deployment"


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Market sizing data based on research
MARKET_DATA = {
    TechnologyDomain.THREE_D_PRINTING: {
        "current_value_billion": 21.9,
        "projected_2032_billion": 101.74,
        "cagr_percent": 23.4,
        "search_growth_percent": 42.3
    },
    TechnologyDomain.AI_ML: {
        "current_value_billion": 196.63,
        "projected_2030_billion": 1811.75,
        "cagr_percent": 37.3,
        "search_growth_percent": 68.5
    },
    TechnologyDomain.IOT: {
        "current_value_billion": 613.29,
        "projected_2030_billion": 3352.67,
        "cagr_percent": 25.1,
        "search_growth_percent": 31.2
    },
    TechnologyDomain.SUSTAINABILITY: {
        "current_value_billion": 44.4,
        "projected_2030_billion": 162.3,
        "cagr_percent": 21.3,
        "search_growth_percent": 55.7
    },
    TechnologyDomain.MOBILITY: {
        "current_value_billion": 103.5,
        "projected_2030_billion": 556.67,
        "cagr_percent": 32.9,
        "search_growth_percent": 47.8
    },
    TechnologyDomain.CYBERSECURITY: {
        "current_value_billion": 266.88,
        "projected_2030_billion": 545.40,
        "cagr_percent": 12.4,
        "search_growth_percent": 28.9
    }
}


# ============================================================================
# DATA MODELS
# ============================================================================
@dataclass
class InnovationProject:
    """Represents an innovation project within the enterprise platform."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    domain: TechnologyDomain = TechnologyDomain.AI_ML
    stage: InnovationStage = InnovationStage.IDEATION
    priority: Priority = Priority.MEDIUM
    risk_level: RiskLevel = RiskLevel.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    budget_allocated: float = 0.0
    budget_spent: float = 0.0
    team_size: int = 0
    expected_roi_percent: float = 0.0
    market_potential_score: float = 0.0
    technical_feasibility_score: float = 0.0
    strategic_alignment_score: float = 0.0
    innovation_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    milestones: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    kpis: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def composite_score(self) -> float:
        """Calculate weighted composite innovation score."""
        weights = {
            'market': 0.30,
            'technical': 0.25,
            'strategic': 0.25,
            'innovation': 0.20
        }
        return (
            self.market_potential_score * weights['market'] +
            self.technical_feasibility_score * weights['technical'] +
            self.strategic_alignment_score * weights['strategic'] +
            self.innovation_score * weights['innovation']
        )

    @property
    def budget_utilization(self) -> float:
        if self.budget_allocated == 0:
            return 0.0
        return (self.budget_spent / self.budget_allocated) * 100

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['domain'] = self.domain.value
        d['stage'] = self.stage.value
        d['priority'] = self.priority.value
        d['risk_level'] = self.risk_level.value
        d['composite_score'] = self.composite_score
        d['budget_utilization'] = self.budget_utilization
        d['created_at'] = self.created_at.isoformat()
        d['updated_at'] = self.updated_at.isoformat()
        return d


@dataclass
class MarketInsight:
    """Represents a market insight or trend."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    domain: TechnologyDomain = TechnologyDomain.AI_ML
    trend_direction: str = "up"  # up, down, stable
    confidence_score: float = 0.0
    impact_score: float = 0.0
    urgency_score: float = 0.0
    sources: List[str] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def action_priority(self) -> float:
        return (self.impact_score * 0.4 + self.urgency_score * 0.35 +
                self.confidence_score * 0.25)


@dataclass
class CompetitorProfile:
    """Competitor intelligence profile."""
    name: str = ""
    market_share_percent: float = 0.0
    innovation_index: float = 0.0
    patent_count: int = 0
    recent_innovations: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    threat_level: RiskLevel = RiskLevel.MEDIUM
    domains: List[TechnologyDomain] = field(default_factory=list)


@dataclass
class ResourceAllocation:
    """Resource allocation for innovation projects."""
    project_id: str = ""
    personnel: int = 0
    budget_monthly: float = 0.0
    infrastructure_cost: float = 0.0
    tools_cost: float = 0.0
    external_services_cost: float = 0.0
    total_monthly_cost: float = 0.0

    def calculate_total(self):
        self.total_monthly_cost = (
            self.budget_monthly + self.infrastructure_cost +
            self.tools_cost + self.external_services_cost
        )
        return self.total_monthly_cost


# ============================================================================
# CORE ENGINE: AI-POWERED INNOVATION SCORING
# ============================================================================
class InnovationScoringEngine:
    """
    AI-powered scoring engine that evaluates innovation projects
    across multiple dimensions using weighted algorithms.
    """

    def __init__(self):
        self.weights = {
            'market_potential': 0.30,
            'technical_feasibility': 0.25,
            'strategic_alignment': 0.20,
            'innovation_novelty': 0.15,
            'risk_adjustment': 0.10
        }
        self.historical_scores: List[Dict] = []
        logger.info("InnovationScoringEngine initialized")

    def score_market_potential(self, project: InnovationProject) -> float:
        """Score based on market size, growth rate, and timing."""
        market = MARKET_DATA.get(project.domain, {})
        cagr = market.get('cagr_percent', 15)
        projected = market.get('projected_2032_billion', 100)

        # Normalize CAGR (0-50% -> 0-100 score)
        cagr_score = min(cagr / 50 * 100, 100)

        # Market size score (logarithmic scale)
        size_score = min(math.log10(max(projected, 1)) / 4 * 100, 100)

        # Timing bonus for high-growth markets
        timing_bonus = 15 if cagr > 30 else (10 if cagr > 20 else 5)

        raw_score = (cagr_score * 0.4 + size_score * 0.4 + timing_bonus * 2)
        return min(max(raw_score, 0), 100)

    def score_technical_feasibility(self, project: InnovationProject) -> float:
        """Score based on technical complexity and available resources."""
        base_score = 70.0

        # Team size impact
        if project.team_size >= 10:
            base_score += 10
        elif project.team_size >= 5:
            base_score += 5
        elif project.team_size < 3:
            base_score -= 10

        # Budget adequacy
        if project.budget_allocated > 500000:
            base_score += 10
        elif project.budget_allocated > 100000:
            base_score += 5
        elif project.budget_allocated < 50000:
            base_score -= 10

        # Stage-based adjustment
        stage_multipliers = {
            InnovationStage.IDEATION: 0.85,
            InnovationStage.RESEARCH: 0.90,
            InnovationStage.PROTOTYPING: 0.95,
            InnovationStage.VALIDATION: 1.0,
            InnovationStage.SCALING: 1.05,
            InnovationStage.DEPLOYMENT: 1.10
        }
        multiplier = stage_multipliers.get(project.stage, 1.0)

        return min(max(base_score * multiplier, 0), 100)

    def score_strategic_alignment(self, project: InnovationProject) -> float:
        """Score based on alignment with enterprise strategy."""
        score = 50.0

        # Priority alignment
        priority_scores = {
            Priority.CRITICAL: 30,
            Priority.HIGH: 20,
            Priority.MEDIUM: 10,
            Priority.LOW: 0
        }
        score += priority_scores.get(project.priority, 10)

        # Tag-based strategic keywords
        strategic_keywords = ['core', 'strategic', 'transformation',
                              'digital', 'enterprise', 'platform']
        tag_matches = sum(1 for tag in project.tags
                         if any(kw in tag.lower() for kw in strategic_keywords))
        score += min(tag_matches * 5, 20)

        return min(max(score, 0), 100)

    def score_innovation_novelty(self, project: InnovationProject) -> float:
        """Score based on novelty and differentiation."""
        base = 60.0

        # Domain novelty bonus
        high_novelty_domains = [
            TechnologyDomain.QUANTUM, TechnologyDomain.BIOTECH,
            TechnologyDomain.THREE_D_PRINTING
        ]
        if project.domain in high_novelty_domains:
            base += 20

        medium_novelty_domains = [
            TechnologyDomain.AI_ML, TechnologyDomain.AR_VR,
            TechnologyDomain.BLOCKCHAIN
        ]
        if project.domain in medium_novelty_domains:
            base += 10

        # Milestone complexity
        if len(project.milestones) > 5:
            base += 10
        elif len(project.milestones) > 3:
            base += 5

        return min(max(base, 0), 100)

    def calculate_risk_adjustment(self, project: InnovationProject) -> float:
        """Calculate risk-based score adjustment."""
        risk_scores = {
            RiskLevel.LOW: 100,
            RiskLevel.MEDIUM: 75,
            RiskLevel.HIGH: 50,
            RiskLevel.CRITICAL: 25
        }
        return risk_scores.get(project.risk_level, 50)

    def compute_composite_score(self, project: InnovationProject) -> Dict[str, float]:
        """Compute all dimension scores and final composite."""
        scores = {
            'market_potential': self.score_market_potential(project),
            'technical_feasibility': self.score_technical_feasibility(project),
            'strategic_alignment': self.score_strategic_alignment(project),
            'innovation_novelty': self.score_innovation_novelty(project),
            'risk_adjustment': self.calculate_risk_adjustment(project)
        }

        composite = sum(
            scores[dim] * self.weights[dim]
            for dim in self.weights
        )
        scores['composite'] = round(composite, 2)

        # Update project scores
        project.market_potential_score = scores['market_potential']
        project.technical_feasibility_score = scores['technical_feasibility']
        project.strategic_alignment_score = scores['strategic_alignment']
        project.innovation_score = scores['innovation_novelty']

        # Store for historical analysis
        self.historical_scores.append({
            'project_id': project.id,
            'timestamp': datetime.now().isoformat(),
            'scores': scores
        })

        logger.info(f"Scored project '{project.name}': composite={scores['composite']:.1f}")
        return scores


# ============================================================================
# MARKET INTELLIGENCE ENGINE
# ============================================================================
class MarketIntelligenceEngine:
    """
    Analyzes market data, trends, and competitive landscape
    to generate actionable innovation insights.
    """

    def __init__(self):
        self.insights: List[MarketInsight] = []
        self.competitors: List[CompetitorProfile] = []
        self.trend_history: Dict[str, List[float]] = defaultdict(list)
        logger.info("MarketIntelligenceEngine initialized")

    def analyze_market_opportunity(self, domain: TechnologyDomain) -> Dict:
        """Deep analysis of market opportunity for a given domain."""
        data = MARKET_DATA.get(domain, {})
        if not data:
            return {"error": "No market data available"}

        current = data['current_value_billion']
        projected = data['projected_2032_billion']
        cagr = data['cagr_percent']
        search_growth = data['search_growth_percent']

        # Calculate market attractiveness
        years = 2032 - datetime.now().year
        growth_factor = (projected / current) if current > 0 else 1
        annual_growth = growth_factor ** (1 / max(years, 1)) - 1

        # Opportunity score (0-100)
        opportunity_score = min(
            (cagr / 40 * 40) +
            (math.log10(max(projected, 1)) / 4 * 30) +
            (search_growth / 70 * 30),
            100
        )

        # Market maturity assessment
        if current > 500:
            maturity = "mature"
        elif current > 100:
            maturity = "growing"
        else:
            maturity = "emerging"

        analysis = {
            "domain": domain.value,
            "current_market_billion": current,
            "projected_market_billion": projected,
            "cagr_percent": cagr,
            "search_interest_growth": search_growth,
            "opportunity_score": round(opportunity_score, 1),
            "market_maturity": maturity,
            "annual_growth_rate": round(annual_growth * 100, 2),
            "investment_recommendation": self._get_investment_rec(opportunity_score),
            "key_drivers": self._get_key_drivers(domain),
            "risk_factors": self._get_risk_factors(domain),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Market analysis for {domain.value}: "
                    f"opportunity={opportunity_score:.1f}")
        return analysis

    def _get_investment_rec(self, score: float) -> str:
        if score >= 80:
            return "AGGRESSIVE INVEST - High growth, strong market signals"
        elif score >= 60:
            return "STRATEGIC INVEST - Solid opportunity with manageable risk"
        elif score >= 40:
            return "SELECTIVE INVEST - Targeted investments in high-potential niches"
        else:
            return "MONITOR - Track developments before committing resources"

    def _get_key_drivers(self, domain: TechnologyDomain) -> List[str]:
        drivers = {
            TechnologyDomain.AI_ML: [
                "Enterprise AI adoption acceleration",
                "Generative AI breakthroughs",
                "Decreasing compute costs",
                "Talent pool expansion",
                "Regulatory framework development"
            ],
            TechnologyDomain.THREE_D_PRINTING: [
                "Industrial manufacturing adoption",
                "Material science advances",
                "Supply chain localization demand",
                "Customization economy growth",
                "Sustainability-driven manufacturing"
            ],
            TechnologyDomain.SUSTAINABILITY: [
                "ESG regulatory requirements",
                "Carbon pricing mechanisms",
                "Consumer sustainability preferences",
                "Circular economy transition",
                "Green technology subsidies"
            ],
            TechnologyDomain.MOBILITY: [
                "EV infrastructure expansion",
                "Autonomous driving progress",
                "Urban mobility demands",
                "Shared economy growth",
                "Battery technology improvements"
            ],
            TechnologyDomain.IOT: [
                "5G network deployment",
                "Edge computing maturity",
                "Industrial IoT adoption",
                "Smart city initiatives",
                "Sensor cost reduction"
            ],
            TechnologyDomain.CYBERSECURITY: [
                "Increasing threat landscape",
                "Zero-trust architecture adoption",
                "AI-powered security tools",
                "Regulatory compliance demands",
                "Remote work security needs"
            ]
        }
        return drivers.get(domain, ["Market expansion", "Technology maturation"])

    def _get_risk_factors(self, domain: TechnologyDomain) -> List[str]:
        risks = {
            TechnologyDomain.AI_ML: [
                "Regulatory uncertainty",
                "Talent competition intensity",
                "Ethical concerns and bias",
                "Compute cost volatility",
                "Data privacy regulations"
            ],
            TechnologyDomain.THREE_D_PRINTING: [
                "IP protection challenges",
                "Material limitations",
                "Quality certification gaps",
                "Scale-up difficulties",
                "Traditional manufacturing resistance"
            ],
            TechnologyDomain.SUSTAINABILITY: [
                "Greenwashing accusations",
                "ROI measurement complexity",
                "Technology readiness gaps",
                "Policy inconsistency",
                "Supply chain dependencies"
            ],
            TechnologyDomain.MOBILITY: [
                "Infrastructure investment needs",
                "Regulatory fragmentation",
                "Consumer adoption barriers",
                "Technology standardization",
                "Capital intensity"
            ],
            TechnologyDomain.IOT: [
                "Security vulnerabilities",
                "Interoperability challenges",
                "Data management complexity",
                "Privacy concerns",
                "Infrastructure dependencies"
            ],
            TechnologyDomain.CYBERSECURITY: [
                "Evolving threat landscape",
                "Skills shortage",
                "Compliance complexity",
                "Technology integration challenges",
                "Cost escalation"
            ]
        }
        return risks.get(domain, ["Market competition", "Technology obsolescence"])

    def generate_competitive_landscape(self) -> List[Dict]:
        """Generate competitive intelligence across domains."""
        competitors_data = [
            {
                "name": "TechGiant Corp",
                "market_share": 22.5,
                "innovation_index": 87.3,
                "patents": 15420,
                "threat": RiskLevel.HIGH,
                "domains": [TechnologyDomain.AI_ML, TechnologyDomain.IOT],
                "strengths": ["Scale", "R&D budget", "Talent pool"],
                "weaknesses": ["Slow to market", "Bureaucratic"]
            },
            {
                "name": "InnovateLab Inc",
                "market_share": 8.2,
                "innovation_index": 94.1,
                "patents": 3200,
                "threat": RiskLevel.HIGH,
                "domains": [TechnologyDomain.AI_ML, TechnologyDomain.THREE_D_PRINTING],
                "strengths": ["Agility", "Breakthrough R&D", "Culture"],
                "weaknesses": ["Limited scale", "Funding constraints"]
            },
            {
                "name": "GreenFuture Systems",
                "market_share": 12.8,
                "innovation_index": 78.5,
                "patents": 5600,
                "threat": RiskLevel.MEDIUM,
                "domains": [TechnologyDomain.SUSTAINABILITY, TechnologyDomain.MOBILITY],
                "strengths": ["First-mover advantage", "Brand loyalty"],
                "weaknesses": ["Narrow focus", "Geographic limits"]
            },
            {
                "name": "SecureNet Global",
                "market_share": 15.3,
                "innovation_index": 82.7,
                "patents": 8900,
                "threat": RiskLevel.MEDIUM,
                "domains": [TechnologyDomain.CYBERSECURITY, TechnologyDomain.AI_ML],
                "strengths": ["Enterprise trust", "Comprehensive suite"],
                "weaknesses": ["Premium pricing", "Integration complexity"]
            },
            {
                "name": "QuantumLeap Tech",
                "market_share": 3.1,
                "innovation_index": 96.8,
                "patents": 890,
                "threat": RiskLevel.LOW,
                "domains": [TechnologyDomain.QUANTUM, TechnologyDomain.AI_ML],
                "strengths": ["Cutting-edge research", "Academic partnerships"],
                "weaknesses": ["Pre-revenue", "Long time-to-market"]
            }
        ]

        landscape = []
        for comp in competitors_data:
            profile = CompetitorProfile(
                name=comp["name"],
                market_share_percent=comp["market_share"],
                innovation_index=comp["innovation_index"],
                patent_count=comp["patents"],
                threat_level=comp["threat"],
                domains=comp["domains"],
                strengths=comp["strengths"],
                weaknesses=comp["weaknesses"]
            )
            self.competitors.append(profile)
            landscape.append({
                "name": profile.name,
                "market_share": profile.market_share_percent,
                "innovation_index": profile.innovation_index,
                "threat_level": profile.threat_level.value,
                "active_domains": [d.value for d in profile.domains],
                "strategic_assessment": self._assess_competitor(profile)
            })

        return landscape

    def _assess_competitor(self, competitor: CompetitorProfile) -> str:
        if competitor.innovation_index > 90 and competitor.threat_level == RiskLevel.HIGH:
            return "CRITICAL THREAT - Direct competitor with superior innovation capability"
        elif competitor.innovation_index > 80:
            return "SIGNIFICANT THREAT - Strong innovator with growing market presence"
        elif competitor.market_share_percent > 15:
            return "MARKET LEADER - Dominant position requires differentiation strategy"
        else:
            return "WATCH LIST - Monitor for emerging competitive threats"

    def create_insight(self, title: str, domain: TechnologyDomain,
                       impact: float, urgency: float,
                       confidence: float, summary: str) -> MarketInsight:
        """Create and store a market insight."""
        insight = MarketInsight(
            title=title,
            domain=domain,
            trend_direction="up" if impact > 60 else "stable",
            confidence_score=confidence,
            impact_score=impact,
            urgency_score=urgency,
            summary=summary,
            recommendations=self._generate_recommendations(domain, impact, urgency)
        )
        self.insights.append(insight)
        logger.info(f"Insight created: '{title}' (priority: {insight.action_priority:.1f})")
        return insight

    def _generate_recommendations(self, domain: TechnologyDomain,
                                   impact: float, urgency: float) -> List[str]:
        base_recs = []
        if impact > 70:
            base_recs.append(f"Prioritize {domain.value} investments immediately")
            base_recs.append("Allocate dedicated innovation team resources")
        if urgency > 70:
            base_recs.append("Accelerate timeline for related initiatives")
            base_recs.append("Establish cross-functional task force")
        if impact > 50 and urgency > 50:
            base_recs.append("Initiate strategic partnerships in this domain")
            base_recs.append("Develop proof-of-concept within 90 days")
        base_recs.append("Monitor competitive movements quarterly")
        base_recs.append("Update innovation portfolio allocation")
        return base_recs

    def get_top_insights(self, n: int = 5) -> List[Dict]:
        """Return top N insights by action priority."""
        sorted_insights = sorted(
            self.insights,
            key=lambda x: x.action_priority,
            reverse=True
        )
        return [
            {
                "title": i.title,
                "domain": i.domain.value,
                "priority_score": round(i.action_priority, 1),
                "impact": i.impact_score,
                "urgency": i.urgency_score,
                "confidence": i.confidence_score,
                "recommendations": i.recommendations[:3]
            }
            for i in sorted_insights[:n]
        ]


# ============================================================================
# PORTFOLIO OPTIMIZATION ENGINE
# ============================================================================
class PortfolioOptimizer:
    """
    Optimizes the innovation portfolio using multi-objective
    optimization considering risk, return, and strategic alignment.
    """

    def __init__(self, total_budget: float = 10_000_000):
        self.total_budget = total_budget
        self.projects: List[InnovationProject] = []
        self.allocations: Dict[str, ResourceAllocation] = {}
        logger.info(f"PortfolioOptimizer initialized with budget: ${total_budget:,.0f}")

    def add_project(self, project: InnovationProject):
        """Add a project to the portfolio."""
        self.projects.append(project)
        logger.info(f"Added project '{project.name}' to portfolio "
                    f"(score: {project.composite_score:.1f})")

    def optimize_allocation(self) -> Dict:
        """
        Optimize budget allocation across portfolio using
        a greedy knapsack approach with strategic constraints.
        """
        if not self.projects:
            return {"error": "No projects in portfolio"}

        # Sort by composite score (descending)
        ranked = sorted(self.projects, key=lambda p: p.composite_score, reverse=True)

        remaining_budget = self.total_budget
        allocations = {}
        total_allocated = 0
        domain_limits = defaultdict(float)
        max_domain_share = 0.35  # No single domain gets more than 35%

        for project in ranked:
            if remaining_budget <= 0:
                break

            # Calculate ideal allocation based on score
            score_ratio = project.composite_score / 100
            ideal_allocation = project.budget_allocated if project.budget_allocated > 0 \
                else (self.total_budget * score_ratio * 0.15)

            # Apply domain cap
            domain_key = project.domain.value
            domain_current = domain_limits[domain_key]
            domain_max = self.total_budget * max_domain_share
            domain_available = max(domain_max - domain_current, 0)

            # Final allocation
            allocation = min(ideal_allocation, remaining_budget, domain_available)

            if allocation > 0:
                alloc = ResourceAllocation(
                    project_id=project.id,
                    personnel=max(project.team_size, 2),
                    budget_monthly=allocation / 12,
                    infrastructure_cost=allocation * 0.15,
                    tools_cost=allocation * 0.08,
                    external_services_cost=allocation * 0.12
                )
                alloc.calculate_total()

                allocations[project.id] = {
                    "project_name": project.name,
                    "domain": project.domain.value,
                    "allocated": round(allocation, 2),
                    "percentage_of_total": round(allocation / self.total_budget * 100, 1),
                    "composite_score": round(project.composite_score, 1),
                    "expected_roi": project.expected_roi_percent,
                    "monthly_burn": round(alloc.total_monthly_cost, 2)
                }

                remaining_budget -= allocation
                total_allocated += allocation
                domain_limits[domain_key] += allocation

        # Portfolio summary
        portfolio_summary = {
            "total_budget": self.total_budget,
            "total_allocated": round(total_allocated, 2),
            "remaining": round(remaining_budget, 2),
            "utilization_percent": round(total_allocated / self.total_budget * 100, 1),
            "projects_funded": len(allocations),
            "projects_total": len(self.projects),
            "domain_distribution": dict(domain_limits),
            "average_score": round(
                statistics.mean([p.composite_score for p in ranked[:len(allocations)]])
                if allocations else 0, 1
            ),
            "weighted_roi": round(
                sum(a["expected_roi"] * a["percentage_of_total"]
                    for a in allocations.values()) /
                max(sum(a["percentage_of_total"] for a in allocations.values()), 1),
                1
            )
        }

        logger.info(f"Portfolio optimized: {len(allocations)}/{len(self.projects)} "
                    f"projects funded, {portfolio_summary['utilization_percent']}% "
                    f"budget utilized")

        return {
            "allocations": allocations,
            "summary": portfolio_summary
        }

    def risk_analysis(self) -> Dict:
        """Analyze portfolio risk distribution."""
        risk_counts = defaultdict(int)
        risk_budgets = defaultdict(float)

        for project in self.projects:
            risk_counts[project.risk_level.value] += 1
            risk_budgets[project.risk_level.value] += project.budget_allocated

        total_projects = len(self.projects) or 1
        total_budget = sum(p.budget_allocated for p in self.projects) or 1

        return {
            "risk_distribution": {
                level: {
                    "count": count,
                    "percentage": round(count / total_projects * 100, 1),
                    "budget": round(risk_budgets[level], 2),
                    "budget_percentage": round(risk_budgets[level] / total_budget * 100, 1)
                }
                for level, count in risk_counts.items()
            },
            "portfolio_risk_score": round(
                sum(
                    {"low": 25, "medium": 50, "high": 75, "critical": 100}.get(level, 50) *
                    count / total_projects
                    for level, count in risk_counts.items()
                ), 1
            ),
            "recommendation": self._risk_recommendation(risk_counts, total_projects)
        }

    def _risk_recommendation(self, risk_counts: Dict, total: int) -> str:
        high_risk_ratio = (risk_counts.get("high", 0) + risk_counts.get("critical", 0)) / total
        if high_risk_ratio > 0.5:
            return "HIGH RISK PORTFOLIO - Rebalance toward lower-risk projects"
        elif high_risk_ratio > 0.3:
            return "ELEVATED RISK - Consider adding stabilizing low-risk projects"
        else:
            return "BALANCED RISK - Portfolio risk profile is healthy"


# ============================================================================
# PREDICTIVE ANALYTICS ENGINE
# ============================================================================
class PredictiveAnalyticsEngine:
    """
    Uses statistical models and trend analysis to predict
    innovation outcomes and market movements.
    """

    def __init__(self):
        self.time_series_data: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.prediction_models: Dict[str, Dict] = {}
        logger.info("PredictiveAnalyticsEngine initialized")

    def add_data_point(self, metric: str, value: float,
                       timestamp: Optional[datetime] = None):
        """Add a time series data point."""
        ts = timestamp or datetime.now()
        self.time_series_data[metric].append((ts, value))

    def forecast(self, metric: str, periods: int = 12) -> Dict:
        """
        Simple exponential smoothing forecast.
        Returns predicted values and confidence intervals.
        """
        data = self.time_series_data.get(metric, [])
        if len(data) < 3:
            return {"error": "Insufficient data for forecasting (need >= 3 points)"}

        values = [d[1] for d in data]
        alpha = 0.3  # Smoothing factor

        # Calculate exponential moving average
        ema = [values[0]]
        for i in range(1, len(values)):
            ema.append(alpha * values[i] + (1 - alpha) * ema[-1])

        # Trend calculation
        if len(ema) >= 2:
            trend = (ema[-1] - ema[0]) / len(ema)
        else:
            trend = 0

        # Volatility (standard deviation of residuals)
        residuals = [values[i] - ema[i] for i in range(len(values))]
        volatility = statistics.stdev(residuals) if len(residuals) > 1 else 0

        # Generate forecasts
        forecasts = []
        last_ema = ema[-1]
        for p in range(1, periods + 1):
            predicted = last_ema + trend * p
            confidence_upper = predicted + 1.96 * volatility * math.sqrt(p)
            confidence_lower = predicted - 1.96 * volatility * math.sqrt(p)
            forecasts.append({
                "period": p,
                "predicted": round(predicted, 2),
                "upper_ci": round(confidence_upper, 2),
                "lower_ci": round(max(confidence_lower, 0), 2),
                "confidence_level": "95%"
            })

        # Trend assessment
        if trend > volatility * 0.5:
            trend_label = "STRONG UPWARD"
        elif trend > 0:
            trend_label = "MODERATE UPWARD"
        elif trend > -volatility * 0.5:
            trend_label = "MODERATE DOWNWARD"
        else:
            trend_label = "STRONG DOWNWARD"

        result = {
            "metric": metric,
            "data_points": len(values),
            "current_value": round(values[-1], 2),
            "ema_current": round(ema[-1], 2),
            "trend_per_period": round(trend, 4),
            "trend_direction": trend_label,
            "volatility": round(volatility, 4),
            "forecasts": forecasts,
            "model_params": {"alpha": alpha, "smoothing": "exponential"}
        }

        self.prediction_models[metric] = result
        logger.info(f"Forecast generated for '{metric}': "
                    f"trend={trend_label}, volatility={volatility:.4f}")
        return result

    def detect_anomalies(self, metric: str, threshold: float = 2.0) -> List[Dict]:
        """Detect anomalies in time series data using z-score method."""
        data = self.time_series_data.get(metric, [])
        if len(data) < 5:
            return []

        values = [d[1] for d in data]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 1

        anomalies = []
        for i, (ts, val) in enumerate(data):
            z_score = (val - mean) / stdev if stdev > 0 else 0
            if abs(z_score) > threshold:
                anomalies.append({
                    "timestamp": ts.isoformat(),
                    "value": val,
                    "z_score": round(z_score, 2),
                    "direction": "above" if z_score > 0 else "below",
                    "severity": "high" if abs(z_score) > 3 else "medium"
                })

        return anomalies

    def correlation_analysis(self, metric_a: str, metric_b: str) -> Dict:
        """Calculate Pearson correlation between two metrics."""
        data_a = [d[1] for d in self.time_series_data.get(metric_a, [])]
        data_b = [d[1] for d in self.time_series_data.get(metric_b, [])]

        min_len = min(len(data_a), len(data_b))
        if min_len < 3:
            return {"error": "Insufficient paired data"}

        a = data_a[:min_len]
        b = data_b[:min_len]

        mean_a = statistics.mean(a)
        mean_b = statistics.mean(b)

        numerator = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(min_len))
        denom_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
        denom_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))

        if denom_a == 0 or denom_b == 0:
            correlation = 0
        else:
            correlation = numerator / (denom_a * denom_b)

        strength = (
            "strong" if abs(correlation) > 0.7 else
            "moderate" if abs(correlation) > 0.4 else
            "weak"
        )
        direction = "positive" if correlation > 0 else "negative"

        return {
            "metric_a": metric_a,
            "metric_b": metric_b,
            "correlation": round(correlation, 4),
            "strength": strength,
            "direction": direction,
            "sample_size": min_len,
            "interpretation": f"{strength.capitalize()} {direction} correlation"
        }


# ============================================================================
# INNOVATION PIPELINE MANAGER
# ============================================================================
class InnovationPipelineManager:
    """
    Manages the end-to-end innovation pipeline from ideation
    through deployment, with stage-gate processes.
    """

    STAGE_GATES = {
        InnovationStage.IDEATION: {
            "min_score": 30,
            "required_kpis": ["market_relevance", "problem_clarity"],
            "max_duration_days": 30,
            "next_stage": InnovationStage.RESEARCH
        },
        InnovationStage.RESEARCH: {
            "min_score": 45,
            "required_kpis": ["market_relevance", "problem_clarity",
                              "technical_viability"],
            "max_duration_days": 90,
            "next_stage": InnovationStage.PROTOTYPING
        },
        InnovationStage.PROTOTYPING: {
            "min_score": 55,
            "required_kpis": ["market_relevance", "problem_clarity",
                              "technical_viability", "prototype_success"],
            "max_duration_days": 120,
            "next_stage": InnovationStage.VALIDATION
        },
        InnovationStage.VALIDATION: {
            "min_score": 65,
            "required_kpis": ["market_relevance", "problem_clarity",
                              "technical_viability", "prototype_success",
                              "user_validation"],
            "max_duration_days": 90,
            "next_stage": InnovationStage.SCALING
        },
        InnovationStage.SCALING: {
            "min_score": 75,
            "required_kpis": ["market_relevance", "problem_clarity",
                              "technical_viability", "prototype_success",
                              "user_validation", "scalability_confirmed"],
            "max_duration_days": 180,
            "next_stage": InnovationStage.DEPLOYMENT
        },
        InnovationStage.DEPLOYMENT: {
            "min_score": 80,
            "required_kpis": ["market_relevance", "problem_clarity",
                              "technical_viability", "prototype_success",
                              "user_validation", "scalability_confirmed",
                              "deployment_readiness"],
            "max_duration_days": 365,
            "next_stage": None
        }
    }

    def __init__(self):
        self.pipeline: Dict[str, InnovationProject] = {}
        self.stage_transitions: List[Dict] = []
        self.blocked_projects: List[Dict] = []
        logger.info("InnovationPipelineManager initialized")

    def submit_project(self, project: InnovationProject) -> Dict:
        """Submit a new project to the pipeline."""
        self.pipeline[project.id] = project
        logger.info(f"Project '{project.name}' submitted to pipeline "
                    f"at stage: {project.stage.value}")
        return {
            "status": "accepted",
            "project_id": project.id,
            "stage": project.stage.value,
            "gate_requirements": self._get_gate_requirements(project.stage)
        }

    def evaluate_stage_gate(self, project_id: str) -> Dict:
        """Evaluate if a project can advance to the next stage."""
        project = self.pipeline.get(project_id)
        if not project:
            return {"error": "Project not found"}

        gate = self.STAGE_GATES.get(project.stage, {})
        if not gate:
            return {"error": "Invalid stage"}

        # Check composite score
        score_check = project.composite_score >= gate["min_score"]

        # Check required KPIs
        kpi_check = all(kpi in project.kpis for kpi in gate["required_kpis"])

        # Check KPI minimum values (all must be >= 50)
        kpi_values_ok = all(
            project.kpis.get(kpi, 0) >= 50
            for kpi in gate["required_kpis"]
        )

        can_advance = score_check and kpi_check and kpi_values_ok

        result = {
            "project_id": project_id,
            "project_name": project.name,
            "current_stage": project.stage.value,
            "composite_score": round(project.composite_score, 1),
            "min_required_score": gate["min_score"],
            "score_passed": score_check,
            "kpis_present": kpi_check,
            "kpis_sufficient": kpi_values_ok,
            "can_advance": can_advance,
            "missing_kpis": [k for k in gate["required_kpis"]
                            if k not in project.kpis],
            "weak_kpis": [k for k in gate["required_kpis"]
                         if project.kpis.get(k, 0) < 50],
            "next_stage": gate["next_stage"].value if gate["next_stage"] else None
        }

        if can_advance and gate["next_stage"]:
            self._advance_project(project, gate["next_stage"])
            result["action"] = "ADVANCED"
        elif not can_advance:
            self.blocked_projects.append({
                "project_id": project_id,
                "reason": "Failed stage gate evaluation",
                "timestamp": datetime.now().isoformat(),
                "details": result
            })
            result["action"] = "BLOCKED"
        else:
            result["action"] = "COMPLETED"

        return result

    def _advance_project(self, project: InnovationProject,
                         next_stage: InnovationStage):
        """Advance project to next stage."""
        old_stage = project.stage
        project.stage = next_stage
        project.updated_at = datetime.now()

        self.stage_transitions.append({
            "project_id": project.id,
            "from_stage": old_stage.value,
            "to_stage": next_stage.value,
            "score": round(project.composite_score, 1),
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Project '{project.name}' advanced: "
                    f"{old_stage.value} -> {next_stage.value}")

    def _get_gate_requirements(self, stage: InnovationStage) -> Dict:
        gate = self.STAGE_GATES.get(stage, {})
        return {
            "min_score": gate.get("min_score", 0),
            "required_kpis": gate.get("required_kpis", []),
            "max_duration_days": gate.get("max_duration_days", 0)
        }

    def get_pipeline_overview(self) -> Dict:
        """Get overview of all projects in the pipeline."""
        stage_counts = defaultdict(int)
        stage_scores = defaultdict(list)

        for project in self.pipeline.values():
            stage_counts[project.stage.value] += 1
            stage_scores[project.stage.value].append(project.composite_score)

        return {
            "total_projects": len(self.pipeline),
            "stage_distribution": dict(stage_counts),
            "average_scores_by_stage": {
                stage: round(statistics.mean(scores), 1)
                for stage, scores in stage_scores.items()
            },
            "blocked_count": len(self.blocked_projects),
            "transitions_count": len(self.stage_transitions),
            "pipeline_health": self._assess_pipeline_health()
        }

    def _assess_pipeline_health(self) -> str:
        if not self.pipeline:
            return "EMPTY - No projects in pipeline"

        total = len(self.pipeline)
        advanced = sum(1 for p in self.pipeline.values()
                      if p.stage.value in ["scaling", "deployment"])
        blocked_ratio = len(self.blocked_projects) / max(total, 1)

        if advanced / total > 0.3 and blocked_ratio < 0.2:
            return "HEALTHY - Good flow and low blockage"
        elif blocked_ratio > 0.4:
            return "CONGESTED - High blockage rate, review criteria"
        elif advanced / total < 0.1:
            return "STAGNANT - Projects not advancing, check support"
        else:
            return "MODERATE - Normal pipeline dynamics"


# ============================================================================
# TECHNOLOGY RADAR
# ============================================================================
class TechnologyRadar:
    """
    Maintains a technology radar tracking adoption readiness
    across the enterprise.
    """

    QUADRANTS = {
        "adopt": "Adopt - Proven, use in production",
        "trial": "Trial - Worth pursuing, pilot projects",
        "assess": "Assess - Explore, understand implications",
        "hold": "Hold - Pause, proceed with caution"
    }

    RINGS = {
        "techniques": "Techniques & Methods",
        "tools": "Tools & Platforms",
        "platforms": "Platforms & Infrastructure",
        "languages": "Languages & Frameworks"
    }

    def __init__(self):
        self.entries: Dict[str, Dict] = {}
        self._initialize_radar()
        logger.info("TechnologyRadar initialized")

    def _initialize_radar(self):
        """Initialize radar with current technology assessments."""
        technologies = [
            {
                "name": "Generative AI (LLMs)",
                "quadrant": "adopt",
                "ring": "tools",
                "maturity": 85,
                "enterprise_readiness": 80,
                "trend": "up",
                "notes": "Production-ready for many use cases"
            },
            {
                "name": "Edge Computing",
                "quadrant": "trial",
                "ring": "platforms",
                "maturity": 70,
                "enterprise_readiness": 65,
                "trend": "up",
                "notes": "Growing adoption in IoT scenarios"
            },
            {
                "name": "Industrial 3D Printing",
                "quadrant": "trial",
                "ring": "tools",
                "maturity": 65,
                "enterprise_readiness": 55,
                "trend": "up",
                "notes": "Rapid growth, 23.4% CAGR projected"
            },
            {
                "name": "Digital Twin Technology",
                "quadrant": "assess",
                "ring": "platforms",
                "maturity": 55,
                "enterprise_readiness": 45,
                "trend": "up",
                "notes": "High potential for manufacturing & mobility"
            },
            {
                "name": "Quantum Computing",
                "quadrant": "assess",
                "ring": "platforms",
                "maturity": 30,
                "enterprise_readiness": 15,
                "trend": "up",
                "notes": "Long-term strategic investment"
            },
            {
                "name": "Blockchain/Smart Contracts",
                "quadrant": "hold",
                "ring": "platforms",
                "maturity": 60,
                "enterprise_readiness": 40,
                "trend": "stable",
                "notes": "Wait for clearer enterprise use cases"
            },
            {
                "name": "Sustainable Tech Platforms",
                "quadrant": "adopt",
                "ring": "platforms",
                "maturity": 75,
                "enterprise_readiness": 70,
                "trend": "up",
                "notes": "ESG compliance driving adoption"
            },
            {
                "name": "Autonomous Systems",
                "quadrant": "assess",
                "ring": "techniques",
                "maturity": 45,
                "enterprise_readiness": 35,
                "trend": "up",
                "notes": "Mobility sector leading adoption"
            },
            {
                "name": "Zero-Trust Security",
                "quadrant": "adopt",
                "ring": "techniques",
                "maturity": 80,
                "enterprise_readiness": 75,
                "trend": "up",
                "notes": "Essential for modern enterprise"
            },
            {
                "name": "Federated Learning",
                "quadrant": "trial",
                "ring": "techniques",
                "maturity": 50,
                "enterprise_readiness": 40,
                "trend": "up",
                "notes": "Privacy-preserving AI training"
            }
        ]

        for tech in technologies:
            self.entries[tech["name"]] = tech

    def get_radar(self) -> Dict:
        """Get full technology radar organized by quadrant."""
        radar = {quadrant: [] for quadrant in self.QUADRANTS}

        for name, entry in self.entries.items():
            radar[entry["quadrant"]].append({
                "name": name,
                "ring": entry["ring"],
                "maturity": entry["maturity"],
                "enterprise_readiness": entry["enterprise_readiness"],
                "trend": entry["trend"],
                "notes": entry["notes"]
            })

        return {
            "quadrants": self.QUADRANTS,
            "rings": self.RINGS,
            "technologies": radar,
            "total_tracked": len(self.entries),
            "generated_at": datetime.now().isoformat()
        }

    def get_recommendations(self, domain: TechnologyDomain) -> List[Dict]:
        """Get technology recommendations for a specific domain."""
        domain_keywords = {
            TechnologyDomain.AI_ML: ["AI", "LLM", "Learning", "Federated"],
            TechnologyDomain.IOT: ["Edge", "IoT", "Digital Twin"],
            TechnologyDomain.THREE_D_PRINTING: ["3D Printing", "Additive"],
            TechnologyDomain.SUSTAINABILITY: ["Sustainable", "Green", "ESG"],
            TechnologyDomain.MOBILITY: ["Autonomous", "Mobility", "Digital Twin"],
            TechnologyDomain.CYBERSECURITY: ["Security", "Zero-Trust", "Blockchain"]
        }

        keywords = domain_keywords.get(domain, [])
        recommendations = []

        for name, entry in self.entries.items():
            if any(kw.lower() in name.lower() for kw in keywords):
                recommendations.append({
                    "technology": name,
                    "quadrant": entry["quadrant"],
                    "action": self.QUADRANTS[entry["quadrant"]],
                    "maturity": entry["maturity"],
                    "readiness": entry["enterprise_readiness"]
                })

        return sorted(recommendations, key=lambda x: x["maturity"], reverse=True)


# ============================================================================
# MAIN PLATFORM ORCHESTRATOR
# ============================================================================
class EnterpriseInnovationPlatform:
    """
    Main orchestrator that integrates all engines and provides
    a unified API for enterprise innovation management.
    """

    def __init__(self, budget: float = 10_000_000):
        self.scoring_engine = InnovationScoringEngine()
        self.market_engine = MarketIntelligenceEngine()
        self.portfolio_optimizer = PortfolioOptimizer(budget)
        self.predictive_engine = PredictiveAnalyticsEngine()
        self.pipeline_manager = InnovationPipelineManager()
        self.technology_radar = TechnologyRadar()

        self.platform_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.now()
        self.api_log: List[Dict] = []

        logger.info(f"EnterpriseInnovationPlatform initialized "
                    f"(ID: {self.platform_id})")

    def _log_api_call(self, endpoint: str, status: str, details: str = ""):
        self.api_log.append({
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "status": status,
            "details": details
        })

    # --- Project Management ---
    def create_project(self, name: str, domain: TechnologyDomain,
                       description: str = "", budget: float = 0,
                       team_size: int = 0, priority: Priority = Priority.MEDIUM,
                       risk: RiskLevel = RiskLevel.MEDIUM,
                       tags: List[str] = None) -> Dict:
        """Create and score a new innovation project."""
        project = InnovationProject(
            name=name,
            description=description,
            domain=domain,
            budget_allocated=budget,
            team_size=team_size,
            priority=priority,
            risk_level=risk,
            tags=tags or []
        )

        # Score the project
        scores = self.scoring_engine.compute_composite_score(project)

        # Add to pipeline
        pipeline_result = self.pipeline_manager.submit_project(project)

        # Add to portfolio
        self.portfolio_optimizer.add_project(project)

        self._log_api_call("create_project", "success", f"Project: {name}")

        return {
            "project": project.to_dict(),
            "scores": scores,
            "pipeline": pipeline_result
        }

    # --- Market Analysis ---
    def analyze_market(self, domain: TechnologyDomain) -> Dict:
        """Perform comprehensive market analysis for a domain."""
        analysis = self.market_engine.analyze_market_opportunity(domain)
        recommendations = self.technology_radar.get_recommendations(domain)
        self._log_api_call("analyze_market", "success", f"Domain: {domain.value}")
        return {
            "market_analysis": analysis,
            "technology_recommendations": recommendations
        }

    # --- Competitive Intelligence ---
    def get_competitive_landscape(self) -> Dict:
        """Get competitive intelligence report."""
        landscape = self.market_engine.generate_competitive_landscape()
        self._log_api_call("get_competitive_landscape", "success")
        return {"competitors": landscape}

    # --- Portfolio Management ---
    def optimize_portfolio(self) -> Dict:
        """Optimize the innovation portfolio allocation."""
        allocation = self.portfolio_optimizer.optimize_allocation()
        risk = self.portfolio_optimizer.risk_analysis()
        self._log_api_call("optimize_portfolio", "success")
        return {
            "allocation": allocation,
            "risk_analysis": risk
        }

    # --- Pipeline Management ---
    def evaluate_pipeline(self) -> Dict:
        """Evaluate all projects at their current stage gates."""
        evaluations = []
        for project_id in self.pipeline_manager.pipeline:
            result = self.pipeline_manager.evaluate_stage_gate(project_id)
            evaluations.append(result)

        overview = self.pipeline_manager.get_pipeline_overview()
        self._log_api_call("evaluate_pipeline", "success")
        return {
            "evaluations": evaluations,
            "overview": overview
        }

    # --- Predictive Analytics ---
    def generate_forecast(self, metric: str, periods: int = 12) -> Dict:
        """Generate forecast for a given metric."""
        forecast = self.predictive_engine.forecast(metric, periods)
        self._log_api_call("generate_forecast", "success", f"Metric: {metric}")
        return forecast

    # --- Technology Radar ---
    def get_technology_radar(self) -> Dict:
        """Get the current technology radar."""
        radar = self.technology_radar.get_radar()
        self._log_api_call("get_technology_radar", "success")
        return radar

    # --- Comprehensive Report ---
    def generate_executive_report(self) -> Dict:
        """Generate a comprehensive executive innovation report."""
        report = {
            "platform_id": self.platform_id,
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {},
            "market_intelligence": {},
            "portfolio_status": {},
            "pipeline_health": {},
            "technology_radar": {},
            "recommendations": []
        }

        # Market overview
        market_summaries = {}
        for domain in TechnologyDomain:
            if domain in MARKET_DATA:
                analysis = self.market_engine.analyze_market_opportunity(domain)
                market_summaries[domain.value] = {
                    "opportunity_score": analysis["opportunity_score"],
                    "maturity": analysis["market_maturity"],
                    "recommendation": analysis["investment_recommendation"]
                }
        report["market_intelligence"] = market_summaries

        # Portfolio status
        portfolio = self.portfolio_optimizer.optimize_portfolio()
        report["portfolio_status"] = portfolio.get("summary", {})

        # Pipeline health
        report["pipeline_health"] = self.pipeline_manager.get_pipeline_overview()

        # Technology radar summary
        radar = self.technology_radar.get_radar()
        report["technology_radar"] = {
            "total_tracked": radar["total_tracked"],
            "adopt_count": len(radar["technologies"].get("adopt", [])),
            "trial_count": len(radar["technologies"].get("trial", [])),
            "assess_count": len(radar["technologies"].get("assess", [])),
            "hold_count": len(radar["technologies"].get("hold", []))
        }

        # Top recommendations
        top_insights = self.market_engine.get_top_insights(5)
        report["recommendations"] = top_insights

        # Executive summary
        report["executive_summary"] = {
            "total_projects": len(self.pipeline_manager.pipeline),
            "portfolio_utilization": report["portfolio_status"].get(
                "utilization_percent", 0),
            "pipeline_health": report["pipeline_health"].get(
                "pipeline_health", "Unknown"),
            "top_opportunity": max(
                market_summaries.items(),
                key=lambda x: x[1]["opportunity_score"]
            )[0] if market_summaries else "N/A",
            "technologies_to_adopt": report["technology_radar"]["adopt_count"],
            "key_actions": [
                "Increase investment in high-opportunity domains",
                "Advance blocked projects through targeted interventions",
                "Establish cross-domain innovation teams",
                "Implement quarterly technology radar reviews"
            ]
        }

        self._log_api_call("generate_executive_report", "success")
        logger.info("Executive report generated successfully")
        return report


# ============================================================================
# DEMONSTRATION / MAIN EXECUTION
# ============================================================================
def run_demo():
    """
    Demonstrates the full capabilities of the Enterprise Innovation Platform
    by creating projects, analyzing markets, optimizing portfolios, and
    generating comprehensive reports.
    """
    print("=" * 80)
    print("  ENTERPRISE INNOVATION PLATFORM v2.0 - DEMONSTRATION")
    print("=" * 80)
    print()

    # Initialize platform
    platform = EnterpriseInnovationPlatform(budget=15_000_000)

    # --- Create Innovation Projects ---
    print("\n📋 CREATING INNOVATION PROJECTS...")
    print("-" * 50)

    projects_config = [
        {
            "name": "AI-Powered Predictive Maintenance",
            "domain": TechnologyDomain.AI_ML,
            "description": "ML system for predicting equipment failures "
                           "in manufacturing using IoT sensor data",
            "budget": 2_500_000,
            "team_size": 8,
            "priority": Priority.HIGH,
            "risk": RiskLevel.MEDIUM,
            "tags": ["ai", "iot", "manufacturing", "predictive"]
        },
        {
            "name": "Sustainable Supply Chain Platform",
            "domain": TechnologyDomain.SUSTAINABILITY,
            "description": "End-to-end platform for tracking and optimizing "
                           "supply chain sustainability metrics",
            "budget": 1_800_000,
            "team_size": 6,
            "priority": Priority.HIGH,
            "risk": RiskLevel.MEDIUM,
            "tags": ["sustainability", "supply-chain", "esg", "core"]
        },
        {
            "name": "Industrial 3D Printing Hub",
            "domain": TechnologyDomain.THREE_D_PRINTING,
            "description": "Centralized 3D printing facility for rapid "
                           "prototyping and low-volume production",
            "budget": 3_200_000,
            "team_size": 5,
            "priority": Priority.MEDIUM,
            "risk": RiskLevel.HIGH,
            "tags": ["3d-printing", "manufacturing", "prototyping"]
        },
        {
            "name": "Smart Mobility Analytics",
            "domain": TechnologyDomain.MOBILITY,
            "description": "Analytics platform for optimizing fleet operations "
                           "and autonomous vehicle integration",
            "budget": 2_000_000,
            "team_size": 7,
            "priority": Priority.MEDIUM,
            "risk": RiskLevel.HIGH,
            "tags": ["mobility", "analytics", "autonomous", "fleet"]
        },
        {
            "name": "Zero-Trust Security Framework",
            "domain": TechnologyDomain.CYBERSECURITY,
            "description": "Enterprise-wide zero-trust architecture "
                           "implementation with AI-driven threat detection",
            "budget": 1_500_000,
            "team_size": 10,
            "priority": Priority.CRITICAL,
            "risk": RiskLevel.MEDIUM,
            "tags": ["security", "zero-trust", "enterprise", "strategic"]
        },
        {
            "name": "IoT Edge Computing Network",
            "domain": TechnologyDomain.IOT,
            "description": "Distributed edge computing infrastructure for "
                           "real-time IoT data processing",
            "budget": 2_800_000,
            "team_size": 6,
            "priority": Priority.HIGH,
            "risk": RiskLevel.MEDIUM,
            "tags": ["iot", "edge-computing", "infrastructure", "platform"]
        },
        {
            "name": "Quantum-Ready Cryptography",
            "domain": TechnologyDomain.QUANTUM,
            "description": "Post-quantum cryptographic systems to future-proof "
                           "enterprise data security",
            "budget": 800_000,
            "team_size": 4,
            "priority": Priority.LOW,
            "risk": RiskLevel.HIGH,
            "tags": ["quantum", "cryptography", "security", "future"]
        },
        {
            "name": "AR/VR Training Platform",
            "domain": TechnologyDomain.AR_VR,
            "description": "Immersive training platform using AR/VR for "
                           "technical skills development",
            "budget": 1_200_000,
            "team_size": 5,
            "priority": Priority.MEDIUM,
            "risk": RiskLevel.LOW,
            "tags": ["ar", "vr", "training", "digital"]
        }
    ]

    created_projects = []
    for config in projects_config:
        result = platform.create_project(**config)
        created_projects.append(result)
        score = result["scores"]["composite"]
        print(f"  ✅ {config['name']}")
        print(f"     Domain: {config['domain'].value} | "
              f"Score: {score:.1f}/100 | Budget: ${config['budget']:,.0f}")

    # --- Market Analysis ---
    print("\n\n📊 MARKET INTELLIGENCE ANALYSIS...")
    print("-" * 50)

    for domain in [TechnologyDomain.AI_ML, TechnologyDomain.THREE_D_PRINTING,
                   TechnologyDomain.SUSTAINABILITY, TechnologyDomain.MOBILITY]:
        analysis = platform.analyze_market(domain)
        ma = analysis["market_analysis"]
        print(f"\n  🔍 {domain.value.upper()}")
        print(f"     Market: ${ma['current_market_billion']}B → "
              f"${ma['projected_market_billion']}B (CAGR: {ma['cagr_percent']}%)")
        print(f"     Opportunity Score: {ma['opportunity_score']}/100")
        print(f"     Maturity: {ma['market_maturity']}")
        print(f"     Recommendation: {ma['investment_recommendation']}")

    # --- Create Market Insights ---
    print("\n\n💡 GENERATING MARKET INSIGHTS...")
    print("-" * 50)

    insights_config = [
        ("Generative AI Reshaping Enterprise Software",
         TechnologyDomain.AI_ML, 92, 85, 88),
        ("3D Printing Reaches Industrial Scale",
         TechnologyDomain.THREE_D_PRINTING, 78, 72, 82),
        ("ESG Regulations Accelerating Green Tech",
         TechnologyDomain.SUSTAINABILITY, 88, 90, 85),
        ("Autonomous Mobility Pilot Programs Expanding",
         TechnologyDomain.MOBILITY, 75, 65, 70),
        ("Edge Computing Critical for IoT at Scale",
         TechnologyDomain.IOT, 82, 78, 80),
        ("Zero-Trust Becoming Compliance Requirement",
         TechnologyDomain.CYBERSECURITY, 85, 88, 90)
    ]

    for title, domain, impact, urgency, confidence in insights_config:
        platform.market_engine.create_insight(
            title=title,
            domain=domain,
            impact=impact,
            urgency=urgency,
            confidence=confidence,
            summary=f"Key insight about {domain.value} trends"
        )
        print(f"  💡 {title}")

    # --- Portfolio Optimization ---
    print("\n\n💰 PORTFOLIO OPTIMIZATION...")
    print("-" * 50)

    portfolio_result = platform.optimize_portfolio()
    summary = portfolio_result["allocation"]["summary"]
    print(f"\n  📈 Portfolio Summary:")
    print(f"     Total Budget: ${summary['total_budget']:,.0f}")
    print(f"     Allocated: ${summary['total_allocated']:,.0f} "
          f"({summary['utilization_percent']}%)")
    print(f"     Projects Funded: {summary['projects_funded']}/"
          f"{summary['projects_total']}")
    print(f"     Average Score: {summary['average_score']}")
    print(f"     Weighted ROI: {summary['weighted_roi']}%")

    print(f"\n  📊 Allocations:")
    for pid, alloc in portfolio_result["allocation"]["allocations"].items():
        print(f"     {alloc['project_name']}: "
              f"${alloc['allocated']:,.0f} ({alloc['percentage_of_total']}%) "
              f"[Score: {alloc['composite_score']}]")

    # Risk Analysis
    risk = portfolio_result["risk_analysis"]
    print(f"\n  ⚠️  Risk Analysis:")
    print(f"     Portfolio Risk Score: {risk['portfolio_risk_score']}/100")
    print(f"     Recommendation: {risk['recommendation']}")

    # --- Technology Radar ---
    print("\n\n🎯 TECHNOLOGY RADAR...")
    print("-" * 50)

    radar = platform.get_technology_radar()
    for quadrant, techs in radar["technologies"].items():
        label = radar["quadrants"][quadrant].split(" - ")[0].upper()
        print(f"\n  [{label}]")
        for tech in techs:
            trend_icon = "📈" if tech["trend"] == "up" else "➡️"
            print(f"    {trend_icon} {tech['name']} "
                  f"(Maturity: {tech['maturity']}, "
                  f"Readiness: {tech['enterprise_readiness']})")

    # --- Predictive Analytics ---
    print("\n\n🔮 PREDICTIVE ANALYTICS...")
    print("-" * 50)

    # Add sample time series data
    base_date = datetime.now() - timedelta(days=365)
    for i in range(12):
        date = base_date + timedelta(days=30 * i)
        # AI market growth simulation
        ai_value = 150 + i * 15 + random.uniform(-10, 10)
        platform.predictive_engine.add_data_point("ai_market_value", ai_value, date)
        # Innovation score trend
        score_value = 45 + i * 3.5 + random.uniform(-5, 5)
        platform.predictive_engine.add_data_point("innovation_score", score_value, date)

    # Generate forecasts
    for metric in ["ai_market_value", "innovation_score"]:
        forecast = platform.generate_forecast(metric, periods=6)
        if "error" not in forecast:
            print(f"\n  📊 Forecast: {metric}")
            print(f"     Current: {forecast['current_value']}")
            print(f"     Trend: {forecast['trend_direction']}")
            print(f"     Volatility: {forecast['volatility']}")
            print(f"     6-period forecast: "
                  f"{forecast['forecasts'][5]['predicted']} "
                  f"(CI: {forecast['forecasts'][5]['lower_ci']} - "
                  f"{forecast['forecasts'][5]['upper_ci']})")

    # --- Pipeline Evaluation ---
    print("\n\n🔄 PIPELINE EVALUATION...")
    print("-" * 50)

    # Add KPIs to some projects to enable advancement
    for i, project_id in enumerate(
            list(platform.pipeline_manager.pipeline.keys())[:3]):
        project = platform.pipeline_manager.pipeline[project_id]
        project.kpis = {
            "market_relevance": 75 + i * 5,
            "problem_clarity": 80 + i * 3,
            "technical_viability": 70 + i * 8,
            "prototype_success": 65 + i * 10,
            "user_validation": 60 + i * 12
        }

    pipeline_eval = platform.evaluate_pipeline()
    overview = pipeline_eval["overview"]
    print(f"\n  📋 Pipeline Overview:")
    print(f"     Total Projects: {overview['total_projects']}")
    print(f"     Stage Distribution: {overview['stage_distribution']}")
    print(f"     Pipeline Health: {overview['pipeline_health']}")
    print(f"     Blocked Projects: {overview['blocked_count']}")

    # --- Competitive Landscape ---
    print("\n\n🏢 COMPETITIVE LANDSCAPE...")
    print("-" * 50)

    comp_landscape = platform.get_competitive_landscape()
    for comp in comp_landscape["competitors"]:
        threat_icon = "🔴" if comp["threat_level"] == "high" else \
                      "🟡" if comp["threat_level"] == "medium" else "🟢"
        print(f"  {threat_icon} {comp['name']}")
        print(f"     Market Share: {comp['market_share']}% | "
              f"Innovation Index: {comp['innovation_index']}")
        print(f"     Assessment: {comp['strategic_assessment']}")

    # --- Executive Report ---
    print("\n\n📑 EXECUTIVE INNOVATION REPORT...")
    print("=" * 50)

    report = platform.generate_executive_report()
    exec_summary = report["executive_summary"]

    print(f"\n  🎯 Key Metrics:")
    print(f"     Total Projects: {exec_summary['total_projects']}")
    print(f"     Portfolio Utilization: {exec_summary['portfolio_utilization']}%")
    print(f"     Pipeline Health: {exec_summary['pipeline_health']}")
    print(f"     Top Opportunity: {exec_summary['top_opportunity']}")
    print(f"     Technologies to Adopt: {exec_summary['technologies_to_adopt']}")

    print(f"\n  🚀 Key Actions:")
    for i, action in enumerate(exec_summary["key_actions"], 1):
        print(f"     {i}. {action}")

    print(f"\n  💡 Top Recommendations:")
    for i, rec in enumerate(report["recommendations"][:3], 1):
        print(f"     {i}. [{rec['domain']}] {rec['title']} "
              f"(Priority: {rec['priority_score']})")

    # --- Final Summary ---
    print("\n" + "=" * 80)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 80)
    print(f"\n  Platform ID: {platform.platform_id}")
    print(f"  API Calls Logged: {len(platform.api_log)}")
    print(f"  Projects Created: {len(created_projects)}")
    print(f"  Market Insights: {len(platform.market_engine.insights)}")
    print(f"  Technologies Tracked: {len(platform.technology_radar.entries)}")
    print(f"\n  All systems operational. Platform ready for enterprise deployment.")
    print()

    return report


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    report = run_demo()

    # Export report as JSON
    output_path = "innovation_report_output.json"
    try:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Report exported to: {output_path}")
    except Exception as e:
        print(f"\n⚠️  Could not export report: {e}")

    print("\n✅ Enterprise Innovation Platform prototype execution complete.")
