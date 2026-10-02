import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  Avatar,
  CapabilityBadge,
  ConnectionPill,
  EmptyState,
  initialsOf,
} from "../components/ui";

describe("design system primitives", () => {
  it("capability badges always carry a text label, not only colour", () => {
    render(<CapabilityBadge state="NON_CONNECTE" />);
    expect(screen.getByText("NON CONNECTÉ")).toBeInTheDocument();
  });

  it("renders every capability taxonomy state", () => {
    const states = ["REEL", "DEMO", "PARTIEL", "NON_CONNECTE", "A_VALIDER"] as const;
    const labels = ["RÉEL", "DÉMO", "PARTIEL", "NON CONNECTÉ", "À VALIDER"];
    states.forEach((s, i) => {
      const { unmount } = render(<CapabilityBadge state={s} />);
      expect(screen.getByText(labels[i])).toBeInTheDocument();
      unmount();
    });
  });

  it("connection pill exposes a textual status", () => {
    render(<ConnectionPill status="offline" />);
    expect(screen.getByText("Hors ligne")).toBeInTheDocument();
  });

  it("empty state shows a message and an action", () => {
    render(
      <EmptyState
        title="Aucun patient pour le moment"
        hint="Commencez par créer votre premier dossier."
        action={<button>Nouveau patient</button>}
      />,
    );
    expect(screen.getByText("Aucun patient pour le moment")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nouveau patient" })).toBeInTheDocument();
  });

  it("derives avatar initials from a full name", () => {
    expect(initialsOf("Awa Ndiaye")).toBe("AN");
    expect(initialsOf("Cher")).toBe("CH");
    render(<Avatar name="Awa Ndiaye" />);
    expect(screen.getByText("AN")).toBeInTheDocument();
  });
});
