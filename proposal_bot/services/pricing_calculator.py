"""Pricing calculator with business logic."""

import json
from typing import Any, Dict, List, Optional

from proposal_bot.schemas.project import ProjectPlan, ResourceAssignment


class PricingCalculator:
    """
    Calculate proposal pricing with business logic and rules.

    This service:
    - Applies standard markup percentages
    - Calculates volume discounts
    - Applies client-specific pricing rules
    - Adds contingency and project management fees
    - Ensures minimum margins are maintained
    """

    def __init__(self):
        """Initialize pricing calculator."""
        self.default_markup = 0.30  # 30% default markup
        self.min_margin = 0.20  # Minimum 20% margin
        self.pm_overhead_rate = 0.15  # 15% PM overhead
        self.contingency_rate = 0.05  # 5% contingency

    def calculate_resource_costs(
        self, resource_assignments: List[ResourceAssignment]
    ) -> Dict[str, float]:
        """
        Calculate costs for all resource assignments.

        Args:
            resource_assignments: List of resource assignments

        Returns:
            Dictionary with cost breakdown
        """
        total_cost = 0.0
        cost_breakdown = {
            "staff_costs": 0.0,
            "vendor_costs": 0.0,
            "other_costs": 0.0,
        }

        for assignment in resource_assignments:
            cost = assignment.cost

            if assignment.resource_type == "staff":
                cost_breakdown["staff_costs"] += cost
            elif assignment.resource_type == "vendor":
                cost_breakdown["vendor_costs"] += cost
            else:
                cost_breakdown["other_costs"] += cost

            total_cost += cost

        cost_breakdown["total_direct_costs"] = total_cost

        return cost_breakdown

    def apply_markup(self, cost: float, markup_rate: Optional[float] = None) -> float:
        """
        Apply markup to a cost.

        Args:
            cost: Base cost
            markup_rate: Markup rate (uses default if not provided)

        Returns:
            Price after markup
        """
        rate = markup_rate if markup_rate is not None else self.default_markup
        return cost * (1 + rate)

    def calculate_volume_discount(
        self, quantity: int, discount_tiers: Dict[str, float]
    ) -> float:
        """
        Calculate volume discount based on quantity.

        Args:
            quantity: Quantity
            discount_tiers: Dictionary of tier thresholds and discount rates

        Returns:
            Discount rate to apply (0.0 - 1.0)
        """
        discount = 0.0

        # Sort tiers by threshold (descending)
        sorted_tiers = sorted(
            [(int(k.rstrip("+")), v) for k, v in discount_tiers.items()],
            key=lambda x: x[0],
            reverse=True,
        )

        for threshold, rate in sorted_tiers:
            if quantity >= threshold:
                discount = rate
                break

        return discount

    def calculate_project_pricing(
        self, project_plan: ProjectPlan, pricing_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate complete project pricing with all business logic.

        Args:
            project_plan: Project plan with resource assignments
            pricing_rules: Optional client-specific pricing rules

        Returns:
            Complete pricing breakdown
        """
        # Calculate base resource costs
        cost_breakdown = self.calculate_resource_costs(project_plan.resource_assignments)

        # Add PM overhead
        pm_overhead = cost_breakdown["total_direct_costs"] * self.pm_overhead_rate
        cost_breakdown["pm_overhead"] = pm_overhead

        # Add contingency
        contingency = cost_breakdown["total_direct_costs"] * self.contingency_rate
        cost_breakdown["contingency"] = contingency

        # Calculate total cost
        total_cost = (
            cost_breakdown["total_direct_costs"] + pm_overhead + contingency
        )
        cost_breakdown["total_cost"] = total_cost

        # Apply markup
        if pricing_rules and "markup_rate" in pricing_rules:
            markup_rate = pricing_rules["markup_rate"]
        else:
            markup_rate = self.default_markup

        total_price = self.apply_markup(total_cost, markup_rate)
        cost_breakdown["markup_rate"] = markup_rate
        cost_breakdown["markup_amount"] = total_price - total_cost

        # Apply volume discounts if applicable
        if pricing_rules and "volume_discount" in pricing_rules:
            discount = pricing_rules["volume_discount"]
            discount_amount = total_price * discount
            total_price -= discount_amount
            cost_breakdown["volume_discount"] = discount
            cost_breakdown["discount_amount"] = discount_amount

        # Apply client-specific discounts
        if pricing_rules and "client_discount" in pricing_rules:
            client_discount = pricing_rules["client_discount"]
            client_discount_amount = total_price * client_discount
            total_price -= client_discount_amount
            cost_breakdown["client_discount"] = client_discount
            cost_breakdown["client_discount_amount"] = client_discount_amount

        # Ensure minimum margin
        margin = (total_price - total_cost) / total_price if total_price > 0 else 0
        if margin < self.min_margin:
            # Adjust price to meet minimum margin
            total_price = total_cost / (1 - self.min_margin)
            cost_breakdown["margin_adjustment"] = True
            cost_breakdown["margin_adjustment_reason"] = (
                f"Adjusted to meet minimum {self.min_margin:.0%} margin"
            )

        cost_breakdown["total_price"] = total_price
        cost_breakdown["final_margin"] = (
            (total_price - total_cost) / total_price if total_price > 0 else 0
        )

        # Calculate price per phase if applicable
        if project_plan.phases:
            phase_costs = self._allocate_costs_to_phases(
                project_plan.phases, total_price
            )
            cost_breakdown["phase_breakdown"] = phase_costs

        return cost_breakdown

    def _allocate_costs_to_phases(
        self, phases: List[Dict[str, Any]], total_price: float
    ) -> List[Dict[str, Any]]:
        """Allocate total price across project phases."""
        phase_breakdown = []

        # Simple allocation based on phase duration or effort
        total_weeks = sum(
            phase.get("duration_weeks", 1) for phase in phases
        )

        for phase in phases:
            phase_weeks = phase.get("duration_weeks", 1)
            phase_price = (phase_weeks / total_weeks) * total_price

            phase_breakdown.append(
                {
                    "phase_name": phase.get("name", "Unknown"),
                    "phase_price": round(phase_price, 2),
                    "percentage": round((phase_weeks / total_weeks) * 100, 1),
                }
            )

        return phase_breakdown

    def generate_pricing_summary(
        self, cost_breakdown: Dict[str, Any]
    ) -> str:
        """
        Generate a formatted pricing summary for the proposal.

        Args:
            cost_breakdown: Cost breakdown dictionary

        Returns:
            Formatted pricing summary text
        """
        summary = f"""
PRICING SUMMARY

Direct Costs:
  Staff Costs:          ${cost_breakdown['staff_costs']:,.2f}
  Vendor Costs:         ${cost_breakdown['vendor_costs']:,.2f}
  Other Costs:          ${cost_breakdown.get('other_costs', 0):,.2f}
  PM Overhead (15%):    ${cost_breakdown['pm_overhead']:,.2f}
  Contingency (5%):     ${cost_breakdown['contingency']:,.2f}
  ────────────────────
  Total Cost:           ${cost_breakdown['total_cost']:,.2f}

Pricing:
  Markup ({cost_breakdown['markup_rate']:.0%}):        ${cost_breakdown['markup_amount']:,.2f}
  Base Price:           ${cost_breakdown['total_cost'] + cost_breakdown['markup_amount']:,.2f}
        """.strip()

        # Add discounts if present
        if "discount_amount" in cost_breakdown:
            summary += f"\n  Volume Discount:      -${cost_breakdown['discount_amount']:,.2f}"

        if "client_discount_amount" in cost_breakdown:
            summary += f"\n  Client Discount:      -${cost_breakdown['client_discount_amount']:,.2f}"

        summary += f"""
  ────────────────────
  TOTAL INVESTMENT:     ${cost_breakdown['total_price']:,.2f}

Margin: {cost_breakdown['final_margin']:.1%}
        """.strip()

        if "phase_breakdown" in cost_breakdown:
            summary += "\n\nPhase Breakdown:\n"
            for phase in cost_breakdown["phase_breakdown"]:
                summary += f"  {phase['phase_name']}: ${phase['phase_price']:,.2f} ({phase['percentage']}%)\n"

        return summary
