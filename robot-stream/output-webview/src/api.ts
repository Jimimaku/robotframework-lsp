interface OutputAPI {
    /**
     * @param runId an id for the run.
     */
    addRun(runId: string): void;
}

interface ClientAPI {
    /**
     * @param runId the id of the run for which we want the contents.
     */
    getRunContents(runId: string): string | string[] | Iterator<string>;

    onClickReference(): void;
}
