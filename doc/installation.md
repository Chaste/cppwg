# Installation

## Pre-requisites

### CastXML

CastXML is **required** for parsing C++ code. To install CastXML on Ubuntu, for example:

```bash
sudo apt-get install castxml
```

If CastXML is not packaged for your platform or you need a newer build,
prebuilt binaries for Linux, macOS, and Windows are published by the
[CastXML-superbuild](https://github.com/CastXML/CastXML-superbuild/releases)
project.

### Clang

Clang is **recommended** because CastXML uses it as a reference compiler.
If `clang++` is not found, it falls back to the available compiler, which may
create parsing errors in certain scenarios. To install Clang on Ubuntu, for example:

```bash
sudo apt-get install clang
```

## Installing cppwg

### Clone (recommended)

To fetch the tool along with example projects (`examples/shapes` and `examples/cells`),
clone the repository and install from your local copy:

```bash
git clone -b v0.4.1 https://github.com/Chaste/cppwg.git
cd cppwg
pip install .
```

:::{note}
Change `-b v0.4.1` to install a different version, or omit the flag entirely to
get the latest development version.
:::

### Direct from GitHub

To install just the tool, without the example projects, install directly from
the GitHub repository:

```bash
pip install git+https://github.com/Chaste/cppwg.git@v0.4.1
```

:::{note}
Change `@v0.4.1` to install a different version, or omit the tag entirely to
install the latest development version.
:::