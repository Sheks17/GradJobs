import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { defaults } from "@/components/filters";
import { parseSearches, SavedSearches } from "@/components/saved-searches";

beforeEach(() => localStorage.clear());
test("invalid browser data is ignored", () => {
  expect(parseSearches("broken")).toEqual([]);
  expect(parseSearches('[{"name":"bad","filters":{}}]')).toEqual([]);
});
test("save, reload and delete filter combinations", () => {
  const onLoad = vi.fn();
  render(
    <SavedSearches
      filters={{ ...defaults, remote: "remote" }}
      query="Python"
      sort="best_match"
      onLoad={onLoad}
    />,
  );
  fireEvent.change(screen.getByLabelText("Saved search name"), {
    target: { value: "Remote Python" },
  });
  fireEvent.click(screen.getByText("Save current search"));
  fireEvent.click(screen.getByText("Remote Python"));
  expect(onLoad).toHaveBeenCalledWith(
    expect.objectContaining({
      query: "Python",
      filters: expect.objectContaining({ remote: "remote" }),
    }),
  );
  fireEvent.click(screen.getByLabelText("Delete saved search Remote Python"));
  expect(screen.queryByText("Remote Python")).toBeNull();
});
