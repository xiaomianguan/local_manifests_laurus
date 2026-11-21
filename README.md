# Local manifests for Xiaomi MI CC 9e (laurus)

Branch `aospa-ruby`: AOSPA Ruby (Android 11).

```bash
# CodeAurora moved to CodeLinaro; AOSPA Ruby's manifest still uses the old host.
git config --global url."https://git.codelinaro.org/clo/la".insteadOf https://source.codeaurora.org/quic/la

repo init -u https://github.com/AOSPA/manifest -b ruby --depth=1 --no-clone-bundle
git clone -b aospa-ruby https://github.com/xiaomianguan/local_manifests_laurus .repo/local_manifests
repo sync -c --no-clone-bundle --no-tags
```

* `laurus.xml`: the laurus device, kernel and vendor repos, frameworks forks
  with the FOD changes, Nicobar HAL branches, and repos that moved upstream.
* `zz-caf-revisions.xml`: pins Qualcomm projects to the exact SHAs of the
  original Ruby releases (LA.QSSI.11.0.r1-12300-qssi.0 and
  LA.UM.9.14.r1-16900-LAHAINA.0), whose tags no longer exist on CodeLinaro.

Then fetch the prebuilt apps and build; see the device tree README.
