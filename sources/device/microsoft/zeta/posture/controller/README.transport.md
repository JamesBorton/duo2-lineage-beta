# Surface panel transport

The controller now uses an original, deliberately minimal Java adapter over
AOSP HwBinder/HwParcel. It includes no vendor-generated interface classes,
copied HIDL contracts, callbacks, enums or general vendor HAL implementation.
Only the panel operations already required by SurfaceHardware are implemented.

Protocol facts: default services use the existing vendor displaytopology 1.0 and
touchpen 1.0 descriptors. Display transaction 1 sends one int32 and returns int32;
transaction 2 returns int32. Touch transaction 1 sends int32 asynchronously and
transaction 4 sends a boolean asynchronously. AOSP IBase ping uses transaction
256921159 with its base descriptor. Controller modes remain 0/1/2.

These interoperability facts were identified from the existing prototype's
call sites, previously available interface declarations and AOSP transport/API
sources. The author has seen those declarations; this is NOT a clean-room
certification or legal opinion about API/reverse-engineering rights. No claim
of permission from their contributors or Microsoft is made. The copied files
and generated bindings are removed from the new build dependency graph.

The narrow adapter intentionally leaves pen/tap callbacks and other unused vendor
methods unsupported. Standard AOSP transport code remains upstream under its
existing license. The new adapter is Apache-2.0 project code. Protocol tests use
injected drivers; a read-only native ping uses AOSP's real service manager on the
emulator. They neither imitate vendor-looking local binders nor register services.
Physical screen transitions still require validation on the resulting candidate.
