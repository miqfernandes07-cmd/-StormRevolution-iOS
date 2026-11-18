# Unlock mode and separate progress

Build 9 adds **Modo trapaça** to the native home screen, enabled by default as requested by the owner. The private title adapter applies character, variant and owned-collection masks for the supported game revision. Content must already exist in the imported game; this does not supply missing DLC or complete every story mission.

Normal progress remains in `Application Support/User`. On first use, the app copies that save directory to `Application Support/CheatUser` through a staging directory and exclusive rename. `Application Support/SelectedUser` is an atomically replaced symlink to the selected profile. The runtime mounts that path only when launching the title. A conflicting regular file or directory is rejected, never replaced. Each profile keeps subsequent progress independently; disabling the switch before Play returns to the normal profile. Updating the app preserves both profiles.

The private hook checks the save-object size and two expected class signatures before changing the verified masks in guest memory. It calls the original game query methods and lets the game write its own save. It does not patch raw file data before checksum validation or populate currency, inventory counts, story state and notification fields indiscriminately. Game offsets, generated title code, existing saves and device logs remain private.

Build 10 also applies the two story fields that the original roster checks for six additional entries. It reapplies the unlocks after a backup restores the active save and at the roster check. These story fields are changed only when using the separate cheat save. The resource availability checks still apply.

The build 9 test extracts the original character query and ten original collection bit-check methods from the private generated title. Against synthetic memory it executes **326,896 checks**, including locked/unlocked results, invalid indices, mismatched signatures, wrong size, idempotence and preservation of every byte outside the selected masks. The category metadata lookup is a bounded test stub. These checks establish mask behavior, not physical gameplay, a complete story or compatibility with other title revisions.

UIKit simulator checks exercise first-copy behavior, writes through the selected alias, preservation of normal progress, repeated switching, conflict refusal, the home toggle and Performance/Safe configuration. `native-session.json` reports the selected profile. Device verification remains necessary.

The extended build 10 test executes 326,914 checks. It proves that with the ordinary character bits already set, the six additional entries fail the original roster check until the separate story fields are set. It verifies the exact byte changes and checks a synthetic resource table with complete entries, missing entries and invalid pointers. The actual installed content and iPhone selection screen still need device verification.
