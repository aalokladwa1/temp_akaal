use std::fs;
use std::path::PathBuf;

#[cfg(target_os = "windows")]
use std::ptr::null_mut;

#[cfg(target_os = "windows")]
#[repr(C)]
struct DataBlob {
    cb_data: u32,
    pb_data: *mut u8,
}

#[cfg(target_os = "windows")]
extern "system" {
    fn CryptProtectData(
        p_data_in: *const DataBlob,
        sz_data_descr: *const u16,
        p_optional_entropy: *const DataBlob,
        pv_reserved: *mut std::ffi::c_void,
        p_prompt_struct: *mut std::ffi::c_void,
        dw_flags: u32,
        p_data_out: *mut DataBlob,
    ) -> i32;

    fn CryptUnprotectData(
        p_data_in: *const DataBlob,
        ppsz_data_descr: *mut *mut u16,
        p_optional_entropy: *const DataBlob,
        pv_reserved: *mut std::ffi::c_void,
        p_prompt_struct: *mut std::ffi::c_void,
        dw_flags: u32,
        p_data_out: *mut DataBlob,
    ) -> i32;

    fn LocalFree(h_mem: *mut std::ffi::c_void) -> *mut std::ffi::c_void;
}

pub fn save_secure_token(app_handle: &tauri::AppHandle<tauri::Wry>, token: &str) -> Result<(), String> {
    let raw_bytes = token.as_bytes();
    let encrypted_bytes = encrypt_bytes(raw_bytes)?;

    let path = get_token_file_path(app_handle)?;
    fs::write(&path, encrypted_bytes)
        .map_err(|e| format!("Failed to write secure token file: {}", e))
}

pub fn load_secure_token(app_handle: &tauri::AppHandle<tauri::Wry>) -> Result<Option<String>, String> {
    let path = get_token_file_path(app_handle)?;
    if !path.exists() {
        return Ok(None);
    }

    let encrypted_bytes = fs::read(&path)
        .map_err(|e| format!("Failed to read secure token file: {}", e))?;

    if encrypted_bytes.is_empty() {
        return Ok(None);
    }

    let decrypted_bytes = decrypt_bytes(&encrypted_bytes)?;
    let token_str = String::from_utf8(decrypted_bytes)
        .map_err(|e| format!("Invalid UTF-8 in decrypted token: {}", e))?;

    Ok(Some(token_str))
}

pub fn clear_secure_token(app_handle: &tauri::AppHandle<tauri::Wry>) -> Result<(), String> {
    let path = get_token_file_path(app_handle)?;
    if path.exists() {
        let _ = fs::remove_file(path);
    }
    Ok(())
}

fn get_token_file_path(app_handle: &tauri::AppHandle<tauri::Wry>) -> Result<PathBuf, String> {
    use tauri::Manager;
    let mut dir = app_handle
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app_config_dir: {}", e))?;
    if !dir.exists() {
        let _ = fs::create_dir_all(&dir);
    }
    dir.push("session.vault");
    Ok(dir)
}

#[cfg(target_os = "windows")]
fn encrypt_bytes(input: &[u8]) -> Result<Vec<u8>, String> {
    let in_blob = DataBlob {
        cb_data: input.len() as u32,
        pb_data: input.as_ptr() as *mut u8,
    };
    let mut out_blob = DataBlob {
        cb_data: 0,
        pb_data: null_mut(),
    };

    let res = unsafe {
        CryptProtectData(
            &in_blob,
            null_mut(),
            null_mut(),
            null_mut(),
            null_mut(),
            0x01, // CRYPTPROTECT_UI_FORBIDDEN
            &mut out_blob,
        )
    };

    if res == 0 {
        return Err("DPAPI CryptProtectData failed".to_string());
    }

    let result_slice = unsafe {
        std::slice::from_raw_parts(out_blob.pb_data, out_blob.cb_data as usize)
    }.to_vec();

    unsafe {
        LocalFree(out_blob.pb_data as *mut std::ffi::c_void);
    }

    Ok(result_slice)
}

#[cfg(not(target_os = "windows"))]
fn encrypt_bytes(input: &[u8]) -> Result<Vec<u8>, String> {
    Ok(input.to_vec())
}

#[cfg(target_os = "windows")]
fn decrypt_bytes(input: &[u8]) -> Result<Vec<u8>, String> {
    let in_blob = DataBlob {
        cb_data: input.len() as u32,
        pb_data: input.as_ptr() as *mut u8,
    };
    let mut out_blob = DataBlob {
        cb_data: 0,
        pb_data: null_mut(),
    };

    let res = unsafe {
        CryptUnprotectData(
            &in_blob,
            null_mut(),
            null_mut(),
            null_mut(),
            null_mut(),
            0x01, // CRYPTPROTECT_UI_FORBIDDEN
            &mut out_blob,
        )
    };

    if res == 0 {
        return Err("DPAPI CryptUnprotectData failed".to_string());
    }

    let result_slice = unsafe {
        std::slice::from_raw_parts(out_blob.pb_data, out_blob.cb_data as usize)
    }.to_vec();

    unsafe {
        LocalFree(out_blob.pb_data as *mut std::ffi::c_void);
    }

    Ok(result_slice)
}

#[cfg(not(target_os = "windows"))]
fn decrypt_bytes(input: &[u8]) -> Result<Vec<u8>, String> {
    Ok(input.to_vec())
}
