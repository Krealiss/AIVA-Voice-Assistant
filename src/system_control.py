import os
import comtypes
from comtypes import GUID, COMMETHOD, IUnknown, CLSCTX_ALL
from comtypes.client import CreateObject
# Додано c_ulong, c_int, c_void_p для правильного визначення типів
from ctypes import cast, POINTER, c_float, c_ulong, c_int, c_void_p, byref

# --- 1. ЯВНЕ ВИЗНАЧЕННЯ ІНТЕРФЕЙСІВ WINDOWS (FIXED TYPES) ---

# ID інтерфейсів (GUID)
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IMMDevice = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
IID_IAudioEndpointVolume = GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

# Тип HRESULT
HRESULT = c_ulong

# Визначення інтерфейсу пристрою (динаміка)
class IMMDevice(IUnknown):
    _iid_ = IID_IMMDevice
    _methods_ = [
        COMMETHOD([], HRESULT, "Activate",
                  (['in'], POINTER(GUID), "iid"),
                  (['in'], c_ulong, "dwClsCtx"),  # Виправлено 0 -> c_ulong
                  (['in'], c_void_p, "pActivationParams"), # Виправлено POINTER -> c_void_p
                  (['out'], POINTER(POINTER(IUnknown)), "ppInterface"))
    ]

# Визначення інтерфейсу енумератора
class IMMDeviceEnumerator(IUnknown):
    _iid_ = IID_IMMDeviceEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, "EnumAudioEndpoints",
                  (['in'], c_int, "dataFlow"), # Виправлено 0 -> c_int
                  (['in'], c_ulong, "dwStateMask"), # Виправлено 0 -> c_ulong
                  (['out'], POINTER(POINTER(IUnknown)), "ppDevices")),
        COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint",
                  (['in'], c_int, "dataFlow"), # eRender = 0
                  (['in'], c_int, "role"),     # eMultimedia = 1
                  (['out'], POINTER(POINTER(IMMDevice)), "ppEndpoint"))
    ]

# Визначення інтерфейсу гучності
class IAudioEndpointVolume(IUnknown):
    _iid_ = IID_IAudioEndpointVolume
    _methods_ = [
        COMMETHOD([], HRESULT, "RegisterControlChangeNotify", (['in'], POINTER(IUnknown), "pNotify")),
        COMMETHOD([], HRESULT, "UnregisterControlChangeNotify", (['in'], POINTER(IUnknown), "pNotify")),
        COMMETHOD([], HRESULT, "GetChannelCount", (['out'], POINTER(c_int), "pnChannelCount")), # Виправлено 0 -> c_int
        COMMETHOD([], HRESULT, "SetMasterVolumeLevel", (['in'], c_float, "fLevelDB"), (['in'], POINTER(GUID), "pguidEventContext")),
        COMMETHOD([], HRESULT, "SetMasterVolumeLevelScalar", (['in'], c_float, "fLevel"), (['in'], POINTER(GUID), "pguidEventContext")),
        COMMETHOD([], HRESULT, "GetMasterVolumeLevel", (['out'], POINTER(c_float), "pfLevelDB")),
        COMMETHOD([], HRESULT, "GetMasterVolumeLevelScalar", (['out'], POINTER(c_float), "pfLevel")),
        COMMETHOD([], HRESULT, "SetChannelVolumeLevel", (['in'], c_int, "nChannel"), (['in'], c_float, "fLevelDB"), (['in'], POINTER(GUID), "pguidEventContext")),
        COMMETHOD([], HRESULT, "SetChannelVolumeLevelScalar", (['in'], c_int, "nChannel"), (['in'], c_float, "fLevel"), (['in'], POINTER(GUID), "pguidEventContext")),
        COMMETHOD([], HRESULT, "GetChannelVolumeLevel", (['in'], c_int, "nChannel"), (['out'], POINTER(c_float), "pfLevelDB")),
        COMMETHOD([], HRESULT, "GetChannelVolumeLevelScalar", (['in'], c_int, "nChannel"), (['out'], POINTER(c_float), "pfLevel")),
        COMMETHOD([], HRESULT, "SetMute", (['in'], c_int, "bMute"), (['in'], POINTER(GUID), "pguidEventContext")), # Виправлено 0 -> c_int
        COMMETHOD([], HRESULT, "GetMute", (['out'], POINTER(c_int), "pbMute")), # Виправлено 0 -> c_int
    ]

# --- 2. КЛАС КЕРУВАННЯ ---

class SystemControl:
    def __init__(self):
        pass

    def _get_volume_interface(self):
        """Отримує інтерфейс гучності, використовуючи визначені вище класи."""
        try:
            # Ініціалізація COM потоку
            try:
                comtypes.CoInitialize()
            except:
                pass

            # Створюємо енумератор і явно вказуємо інтерфейс IMMDeviceEnumerator
            enumerator = CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            
            # Отримуємо дефолтний пристрій (0=eRender, 1=eMultimedia)
            device = enumerator.GetDefaultAudioEndpoint(0, 1)
            
            # Активуємо інтерфейс гучності
            # Activate повертає загальний IUnknown, тому ми його кастимо до IAudioEndpointVolume
            interface = device.Activate(IID_IAudioEndpointVolume, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            return volume, None
            
        except Exception as e:
            return None, f"Windows Audio Error: {str(e)}"

    def set_volume(self, level: int) -> str:
        volume, error = self._get_volume_interface()
        if error or not volume: return f"❌ Помилка: {error}"
        
        level = max(0, min(100, level))
        scalar = float(level) / 100.0
        
        try:
            # GUID(None) передає NULL у C++
            volume.SetMasterVolumeLevelScalar(scalar, None)
            return f"🔊 Гучність: {level}%"
        except Exception as e:
            return f"❌ Збій: {e}"

    def change_volume(self, delta: int) -> str:
        volume, error = self._get_volume_interface()
        if error or not volume: return f"❌ Помилка: {error}"

        try:
            # Отримуємо поточний рівень
            current = c_float()
            volume.GetMasterVolumeLevelScalar(byref(current))

            new_vol = max(0.0, min(1.0, current.value + (delta / 100.0)))
            volume.SetMasterVolumeLevelScalar(new_vol, None)

            val = int(new_vol * 100)
            return f"🔊 Гучність: {val}%"
        except Exception as e:
            return f"❌ Збій: {e}"

    def mute_toggle(self) -> str:
        volume, error = self._get_volume_interface()
        if error or not volume: return f"❌ Помилка: {error}"

        try:
            current_mute = c_int()
            volume.GetMute(byref(current_mute))

            # Інвертуємо (0 -> 1, 1 -> 0)
            new_state = 0 if current_mute.value else 1
            volume.SetMute(new_state, None)

            status = "Вимкнено" if new_state else "Увімкнено"
            return f"🔇 Звук: {status}"
        except Exception as e:
            return f"❌ Збій муту: {e}"

    def pc_shutdown(self) -> str:
        # Використовуємо повний шлях до файлу shutdown.exe
        # Параметр /s - вимкнення, /t 30 - таймер 30 секунд
        os.system(r"C:\Windows\System32\shutdown.exe /s /t 30")
        return "👋 Вимикаю ПК через 30 с. ('Скасувати' для відміни)"

    def pc_cancel_shutdown(self) -> str:
        # Параметр /a - скасування (abort)
        os.system(r"C:\Windows\System32\shutdown.exe /a")
        return "✅ Вимкнення скасовано."

sys_ctrl = SystemControl()