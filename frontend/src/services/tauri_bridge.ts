type TauriCore = {
  invoke?: (command: string, args?: Record<string, unknown>) => Promise<unknown>;
};

type TauriWindow = Window & {
  __TAURI__?: {
    core?: TauriCore;
  };
};

function getInvoke(): ((command: string, args?: Record<string, unknown>) => Promise<unknown>) | null {
  const win = window as TauriWindow;
  const invoke = win.__TAURI__?.core?.invoke;
  return typeof invoke === "function" ? invoke : null;
}

export async function invokeTauri(command: string, args?: Record<string, unknown>): Promise<unknown> {
  const invoke = getInvoke();
  if (!invoke) {
    return null;
  }
  return invoke(command, args);
}

export function isTauriRuntime(): boolean {
  return getInvoke() !== null;
}
