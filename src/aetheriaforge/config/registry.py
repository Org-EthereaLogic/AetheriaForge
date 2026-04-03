"""Dataset registry for managing multiple versioned forge contracts."""

from __future__ import annotations

from pathlib import Path

from aetheriaforge.config.contract import ForgeContract


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a semver-like string into a comparable tuple of ints.

    Non-numeric segments are treated as 0 so that ``"1.0.0-beta"`` still
    sorts after ``"0.9.0"`` without crashing.
    """
    parts: list[int] = []
    for segment in version.split("."):
        token = segment.split("-")[0]
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class DatasetRegistry:
    """In-memory registry of versioned :class:`ForgeContract` instances.

    Each dataset is identified by its *name* and *version*.  A name+version
    pair may only be registered once; attempts to overwrite raise
    ``ValueError``.
    """

    def __init__(self) -> None:
        # {dataset_name: {version_string: ForgeContract}}
        self._contracts: dict[str, dict[str, ForgeContract]] = {}

    # -- mutators -------------------------------------------------------------

    def register(self, contract: ForgeContract) -> None:
        """Register a :class:`ForgeContract`.

        Raises ``ValueError`` if the same name+version is already registered.
        """
        name = contract.dataset_name
        version = contract.dataset_version

        if name in self._contracts and version in self._contracts[name]:
            msg = (
                f"Contract already registered: "
                f"{name!r} version {version!r}"
            )
            raise ValueError(msg)

        self._contracts.setdefault(name, {})[version] = contract

    # -- queries --------------------------------------------------------------

    def get(
        self, name: str, version: str | None = None
    ) -> ForgeContract:
        """Return a registered contract by *name* and optional *version*.

        When *version* is ``None``, the latest version (by semver ordering)
        is returned.  Raises ``KeyError`` if the dataset or version is not
        found.
        """
        versions = self._contracts.get(name)
        if not versions:
            msg = f"No contracts registered for dataset {name!r}"
            raise KeyError(msg)

        if version is not None:
            if version not in versions:
                msg = f"Version {version!r} not found for dataset {name!r}"
                raise KeyError(msg)
            return versions[version]

        latest_version = max(versions, key=_version_tuple)
        return versions[latest_version]

    def list_datasets(self) -> list[str]:
        """Return sorted names of all registered datasets."""
        return sorted(self._contracts)

    def list_versions(self, name: str) -> list[str]:
        """Return versions registered for *name*, sorted by semver ascending.

        Raises ``KeyError`` if *name* is not registered.
        """
        versions = self._contracts.get(name)
        if versions is None:
            msg = f"No contracts registered for dataset {name!r}"
            raise KeyError(msg)
        return sorted(versions, key=_version_tuple)

    def __len__(self) -> int:
        """Return the total number of registered name+version pairs."""
        return sum(len(v) for v in self._contracts.values())

    def __contains__(self, name: str) -> bool:  # type: ignore[override]
        """Check whether *name* has at least one registered version."""
        return name in self._contracts

    # -- bulk loading ---------------------------------------------------------

    @classmethod
    def from_directory(cls, path: Path) -> DatasetRegistry:
        """Load all ``*.yml`` / ``*.yaml`` files from *path* into a new registry."""
        registry = cls()
        for yaml_path in sorted(path.iterdir()):
            if yaml_path.suffix in (".yml", ".yaml"):
                contract = ForgeContract.from_yaml(yaml_path)
                registry.register(contract)
        return registry
