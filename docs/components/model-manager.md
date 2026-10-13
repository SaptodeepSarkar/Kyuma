# Model Manager (Lava / Laya)

Spawned service owned by the harness. Serves the decision model behind an API.

- Keeps the Laya model loaded in memory.
- Loads it onto the correct GPU; handles offloading.
- Manages context across calls.
- Exposes the API interface the harness calls. Harness never loads the model directly.

Note: vault names it "Lava Model Manager" but describes the Laya model; decision model
choice (Jev vs Laya) still open. Kept the vault name in the title so it stays searchable.
