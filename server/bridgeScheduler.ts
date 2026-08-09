export class BridgeSchedulerBusyError extends Error {
  readonly code = "BRIDGE_BUSY";
  readonly status = 429;

  constructor() {
    super("BRIDGE_BUSY");
    this.name = "BridgeSchedulerBusyError";
  }
}

type QueuedJob<T> = {
  work: () => Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
};

export class BridgeScheduler {
  readonly concurrency: number;
  readonly maxQueue: number;
  #active = 0;
  #closed = false;
  #queue: Array<QueuedJob<unknown>> = [];

  constructor(options: { concurrency: number; maxQueue: number }) {
    if (options.concurrency < 1 || options.maxQueue < 0) {
      throw new Error("INVALID_BRIDGE_SCHEDULER_LIMITS");
    }
    this.concurrency = options.concurrency;
    this.maxQueue = options.maxQueue;
  }

  schedule<T>(work: () => Promise<T>): Promise<T> {
    if (this.#closed || (this.#active >= this.concurrency && this.#queue.length >= this.maxQueue)) {
      return Promise.reject(new BridgeSchedulerBusyError());
    }
    return new Promise<T>((resolve, reject) => {
      const job: QueuedJob<T> = { work, resolve, reject };
      if (this.#active < this.concurrency) this.#start(job);
      else this.#queue.push(job as QueuedJob<unknown>);
    });
  }

  close(): void {
    this.#closed = true;
    for (const job of this.#queue.splice(0)) {
      job.reject(new BridgeSchedulerBusyError());
    }
  }

  #start<T>(job: QueuedJob<T>): void {
    this.#active += 1;
    Promise.resolve()
      .then(job.work)
      .then(job.resolve, job.reject)
      .finally(() => {
        this.#active -= 1;
        const next = this.#queue.shift();
        if (next) this.#start(next);
      });
  }
}
