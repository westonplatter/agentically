## Pandas

### Principles

1. **Use vectorized operations** - Avoid iterating over rows with `for` loops or `.iterrows()`. Use built-in vectorized methods for performance.

2. **Chain methods** - Use method chaining (`.pipe()`, `.assign()`, `.query()`) for readable, declarative transformations.

3. **Be explicit with dtypes** - Specify dtypes when reading data and use `.astype()` to enforce types. This prevents silent type coercion bugs.

4. **Prefer `.loc` and `.iloc`** - Use explicit indexing instead of chained indexing to avoid `SettingWithCopyWarning` and ensure predictable behavior.

5. **Handle missing data intentionally** - Use `.isna()`, `.fillna()`, or `.dropna()` explicitly. Never assume data is complete.

6. **Use `.copy()` when needed** - Create explicit copies when modifying subsets to avoid unintended mutations to the original DataFrame.
