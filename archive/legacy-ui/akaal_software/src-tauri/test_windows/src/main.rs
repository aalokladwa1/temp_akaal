use std::fs::OpenOptions;
use std::io::{Read, Write};

fn main() {
    println!("Connecting to AKAAL Engine Named Pipe...");
    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .open(r"\\.\pipe\akaal_engine")
        .expect("Failed to connect to IPC pipe");

    // 1. Invoke create_project
    let req1 = r#"{"request_id":"req-1","capability":"create_project","payload":"{\"project_name\":\"Enterprise PostgreSQL Core Migration\"}"}"#;
    let len1 = (req1.len() as u32).to_be_bytes();
    let mut pkt1 = Vec::with_capacity(4 + req1.len());
    pkt1.extend_from_slice(&len1);
    pkt1.extend_from_slice(req1.as_bytes());
    file.write_all(&pkt1).unwrap();
    file.flush().unwrap();

    let mut resp_len_buf1 = [0u8; 4];
    file.read_exact(&mut resp_len_buf1).unwrap();
    let resp_len1 = u32::from_be_bytes(resp_len_buf1) as usize;
    let mut resp_buf1 = vec![0u8; resp_len1];
    file.read_exact(&mut resp_buf1).unwrap();
    println!("Response 1 (create_project): {}", String::from_utf8_lossy(&resp_buf1));

    // 2. Invoke start_scout
    let req2 = r#"{"request_id":"req-2","capability":"start_scout","payload":"{\"migration_id\":\"mig-12345\"}"}"#;
    let len2 = (req2.len() as u32).to_be_bytes();
    let mut pkt2 = Vec::with_capacity(4 + req2.len());
    pkt2.extend_from_slice(&len2);
    pkt2.extend_from_slice(req2.as_bytes());
    file.write_all(&pkt2).unwrap();
    file.flush().unwrap();

    let mut resp_len_buf2 = [0u8; 4];
    file.read_exact(&mut resp_len_buf2).unwrap();
    let resp_len2 = u32::from_be_bytes(resp_len_buf2) as usize;
    let mut resp_buf2 = vec![0u8; resp_len2];
    file.read_exact(&mut resp_buf2).unwrap();
    println!("Response 2 (start_scout): {}", String::from_utf8_lossy(&resp_buf2));
}
