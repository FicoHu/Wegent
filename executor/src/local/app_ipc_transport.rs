// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

use std::path::PathBuf;

#[cfg(unix)]
use std::{fs, io};

use crate::{
    local::app_ipc::{app_ipc_listening_log_line, AppIpcServer},
    logging::write_executor_log_line,
};

#[cfg(unix)]
use tokio::net::UnixListener;

#[cfg(unix)]
pub async fn serve_forever(
    server: AppIpcServer,
    device_id: String,
    socket_path: PathBuf,
) -> Result<(), String> {
    prepare_socket_path(&socket_path).map_err(|error| {
        format!(
            "failed to prepare app IPC socket {}: {error}",
            socket_path.display()
        )
    })?;
    let listener = UnixListener::bind(&socket_path).map_err(|error| {
        format!(
            "failed to bind app IPC socket {}: {error}",
            socket_path.display()
        )
    })?;
    set_socket_permissions(&socket_path);
    write_executor_log_line(&app_ipc_listening_log_line(
        &device_id,
        &socket_path.display().to_string(),
    ));

    loop {
        let (stream, _) = listener.accept().await.map_err(|error| {
            format!(
                "failed to accept app IPC client on {}: {error}",
                socket_path.display()
            )
        })?;
        let server = server.clone();
        tokio::spawn(async move {
            if let Err(error) = server.handle_stream(stream).await {
                eprintln!("app IPC client error: {error}");
            }
        });
    }
}

#[cfg(not(unix))]
pub async fn serve_forever(
    _server: AppIpcServer,
    _device_id: String,
    _socket_path: PathBuf,
) -> Result<(), String> {
    Err("app IPC sidecar is not available on this platform".to_owned())
}

#[cfg(unix)]
fn prepare_socket_path(socket_path: &std::path::Path) -> io::Result<()> {
    if let Some(parent) = socket_path.parent() {
        fs::create_dir_all(parent)?;
    }
    match fs::remove_file(socket_path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error),
    }
}

#[cfg(unix)]
fn set_socket_permissions(socket_path: &std::path::Path) {
    use std::os::unix::fs::PermissionsExt;

    let _ = fs::set_permissions(socket_path, fs::Permissions::from_mode(0o600));
}
