export const filterByFields = <T>(
  items: T[],
  term: string,
  selectors: Array<(item: T) => unknown>,
): T[] => {
  const normalized = term.trim().toLowerCase();
  if (!normalized) return items;
  return items.filter((item) => {
    for (const select of selectors) {
      const value = select(item);
      if (value == null) continue;
      const text = String(value).toLowerCase();
      if (text.includes(normalized)) return true;
    }
    return false;
  });
};
