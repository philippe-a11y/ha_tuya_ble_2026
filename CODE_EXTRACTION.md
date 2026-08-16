# Extracting Tuya BLE device credentials

Some Tuya BLE devices can be controlled by the Tuya mobile app but are not
returned by the public Tuya Cloud API. This is especially common for BLE
subdevices connected through a Tuya Bluetooth gateway. In that situation the
integration cannot obtain the per-device encryption material automatically.

This document describes the procedure used to inspect the Tuya Android app's
in-memory device cache and recover the credentials for a device you own.

> [!WARNING]
> Device keys are credentials. Only inspect devices and accounts you own or are
> authorized to administer. Never publish keys, device IDs, account data,
> Frida logs, screenshots containing secrets, or Home Assistant config-entry
> exports.

## What is extracted

The Tuya SDK stores known devices as
`com.thingclips.smart.sdk.bean.DeviceBean` objects. The useful fields are:

| Field | Purpose |
|---|---|
| `devId` | Tuya device ID |
| `uuid` | BLE device UUID used by the Tuya protocol |
| `localKey` | 16-byte per-device local encryption key |
| `secKey` | Optional 16-byte secondary device key |
| `productId` | Selects the device implementation and datapoint mapping |
| `categoryCode` | Tuya device category |
| `mac` | Tuya-reported device MAC address; this can differ from the address advertised to Home Assistant |
| `parentDevId` | Gateway ID when the device is a BLE subdevice |
| `openProxy` | Indicates that Tuya gateway/proxy operation is enabled |

The keys are not model-wide constants. A second Brandson Coolbox of the same
model needs its own `devId`, `uuid`, `localKey`, and, when present, `secKey`.

## Tested environment

The successful setup used:

- an Apple silicon Mac;
- an Android Studio AVD with an ARM64 Android 14 AOSP `userdebug` image;
- root ADB access in the emulator;
- **Tuya App 7.6.0 (build/version code 819)**, Android package
  `com.tuya.smart`, installed from the APKMirror `.apkm` bundle containing the
  ARM64 split;
- matching Frida client and server versions.

The exact bundle used during testing was named:

```text
com.tuya.smart_7.6.0-819_2arch_cce0947aeda2a1926c1e263e1524bf9b_apkmirror.com.apkm
```

Later Tuya releases may rename SDK classes or fields, add anti-instrumentation
checks, or behave differently under Frida. If reproducing the documented
procedure, start with version 7.6.0 (819).

Google Play services are not required for the extraction itself. The Tuya app
must, however, be able to sign in and populate its device list.

## 1. Verify the emulator and architecture

```shell
adb devices -l
adb root
adb shell id
adb shell getprop ro.product.cpu.abilist
```

Expected results include `uid=0(root)` and `arm64-v8a`. Use a Frida server
binary matching both the emulator ABI and the local Frida client version.

## 2. Start Frida server

Replace the source path with the location of your matching ARM64 Frida server:

```shell
adb push ./frida-server /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server
adb shell '/data/local/tmp/frida-server >/dev/null 2>&1 &'
frida --version
frida-ps -U
```

If `frida-ps -U` lists Android processes, the connection is ready.

## 3. Sign in and load the Tuya device list

Install the Tuya app in the emulator, sign in to the same Tuya account used by
the device, and open the Home/device screen. Confirm that the target device is
visible and can be controlled.

The target does not have to be within Bluetooth range if the app can reach it
through a Tuya Bluetooth gateway. The credentials are read from the app's
device cache, not from a live BLE handshake.

## 4. Attach to the running app

Start the Tuya app normally and attach to the foreground process:

```shell
frida -U -F
```

Attaching to the already running foreground app was significantly more stable
than spawning it with `frida -U -f com.tuya.smart`. Before running any
inspection script, verify that a minimal `Java.perform(...)` smoke test remains
attached without crashing the app.

## 5. Inspect only `DeviceBean`

Avoid broad class enumeration and unrestricted heap scans. On Android 14 ARM64
they can crash ART with a native `SIGSEGV`. Limit inspection to the known
`DeviceBean` class, and filter candidates by the visible device name,
`productId`, or `devId` before reading fields.

The following is intentionally a template rather than a copy-and-paste secret
dumper. It prints only a small allowlist of fields, and it masks both keys by
default:

```javascript
Java.perform(function () {
  const DeviceBean = Java.use("com.thingclips.smart.sdk.bean.DeviceBean");
  const targetProductId = "YOUR_PRODUCT_ID";

  Java.choose(DeviceBean.$className, {
    onMatch(instance) {
      const productId = String(instance.productId.value || "");
      if (productId !== targetProductId) return;

      const mask = value => {
        const text = String(value || "");
        return text.length < 5 ? "<redacted>" : text.slice(0, 2) + "…" + text.slice(-2);
      };

      console.log("name=" + String(instance.name.value || ""));
      console.log("devId=" + String(instance.devId.value || ""));
      console.log("uuid=" + String(instance.uuid.value || ""));
      console.log("productId=" + productId);
      console.log("category=" + String(instance.categoryCode.value || ""));
      console.log("mac=" + String(instance.mac.value || ""));
      console.log("localKey=" + mask(instance.localKey.value));
      console.log("secKey=" + mask(instance.secKey.value));
    },
    onComplete() {
      console.log("DeviceBean inspection complete");
    },
  });
});
```

For actual Home Assistant setup, capture the full key values only in a private,
temporary copy of the script or through an interactive accessor. Do not save
the resulting terminal output in a public repository or support ticket.

## 6. Configure Home Assistant manually

In Home Assistant, add **Tuya BLE**, choose **Manual BLE credentials**, select
the discovered Bluetooth address, and enter:

- device name;
- device ID (`devId`);
- UUID;
- local key;
- optional secondary key (`secKey`);
- category code;
- product ID.

The Bluetooth address must come from Home Assistant's discovery result. Do not
assume that the Tuya `mac` field is the address Home Assistant sees; BLE address
randomization and gateway metadata can make them different.

After saving, the integration stores the secrets in the Home Assistant config
entry. The options form deliberately leaves saved secret fields blank when
editing; an empty value preserves the existing secret.

## Brandson Coolbox identifiers

The currently supported Brandson model uses:

| Property | Value |
|---|---|
| Category | `xbx_2b_2` |
| Product ID | `boagb65r` |

These two identifiers describe the model and may be shared. All device IDs,
UUIDs, keys, and Bluetooth addresses remain device-specific.

## Troubleshooting

### `Failed to attach: process not found`

Open the Tuya app, leave it in the foreground, and use `frida -U -F`. A PID
obtained earlier may already be stale because Android restarted the process.

### `agent connection closed unexpectedly`

Confirm that client and server versions match exactly, the server binary is for
ARM64, and `frida-ps -U` works. Restart the Frida server if necessary.

### Tuya crashes with `SIGSEGV` in `libart.so`

Stop using spawn mode and broad heap/class scans. Launch Tuya normally, attach
to the foreground app, verify a minimal Java smoke test, and inspect only
`DeviceBean` with a narrow filter.

### The Tuya app works through a gateway, but Home Assistant does not

The Tuya gateway path only helps populate the mobile app's cache. This
integration communicates locally over BLE. Home Assistant therefore still
needs direct Bluetooth coverage or a compatible Home Assistant Bluetooth
proxy within range of the Coolbox.

## Cleanup

When extraction is complete:

```shell
adb shell pkill -f frida-server
adb shell rm /data/local/tmp/frida-server
```

Delete temporary scripts and logs that contain unmasked keys. Keep credentials
only in a secure password manager and in the Home Assistant config entry that
needs them.
