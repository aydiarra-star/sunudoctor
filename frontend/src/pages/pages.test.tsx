import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Landing } from "../pages/Landing";
import { Status } from "../pages/Status";

describe("Landing page", () => {
  it("shows the brand, tagline and CTAs", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(/SunuDoctor/).length).toBeGreaterThan(0);
    expect(screen.getByText(/La santé connectée, au service de tous/)).toBeInTheDocument();
    expect(screen.getAllByText("Créer mon compte").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Découvrir SunuDoctor").length).toBeGreaterThan(0);
  });

  it("labels pricing as launch pricing (no fake market study)", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(/Tarifs de lancement/).length).toBeGreaterThan(0);
  });
});

describe("Status page honesty", () => {
  it("classifies capabilities explicitly", () => {
    render(
      <MemoryRouter>
        <Status />
      </MemoryRouter>,
    );
    expect(screen.getAllByText("RÉEL").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DÉMO").length).toBeGreaterThan(0);
    expect(screen.getAllByText("NON CONNECTÉ").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Wolof/).length).toBeGreaterThan(0);
  });
});
