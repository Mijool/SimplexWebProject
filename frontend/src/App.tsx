import React, { useState } from "react";

import "./App.css";



// 1. Strict TypeScript Contracts mirroring Python's Pydantic Models

type Inequality = "<=" | ">=";



interface SimplexRequestPayload {

  c: number[];

  A: number[][];

  b: number[];

  inequalities: Inequality[];

  maximize: boolean;

}



interface SimplexResponseData {

  status: string;

  optimal_z: number;

  optimal_variables: number[];

  execution_time_ms: number;

  plot_base64: string | null;

}



const API_BASE_URL: string =

  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";



export default function App(): React.JSX.Element {

  // 2. Strongly-Typed React State Hooks

  const [numVars, setNumVars] = useState<number>(2);

  const [numConstraints, setNumConstraints] = useState<number>(3);

  const [maximize, setMaximize] = useState<boolean>(true);



  // Store matrix inputs as strings so users can type negatives/decimals smoothly

  const [objCoeffs, setObjCoeffs] = useState<string[]>(["3", "5"]);

  const [matrixA, setMatrixA] = useState<string[][]>([

    ["1", "0"],

    ["0", "2"],

    ["3", "2"],

  ]);

  const [rhsB, setRhsB] = useState<string[]>(["4", "12", "18"]);

  const [inequalities, setInequalities] = useState<Inequality[]>([

    "<=",

    "<=",

    "<=",

  ]);



  const [result, setResult] = useState<SimplexResponseData | null>(null);

  const [loading, setLoading] = useState<boolean>(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);



  // 3. Resize Grid While Preserving Existing Values

  const handleResizeGrid = (newVars: number, newConstraints: number): void => {

    setNumVars(newVars);

    setNumConstraints(newConstraints);



    setObjCoeffs((prev: string[]) =>

      Array.from({ length: newVars }, (_, j) => prev[j] ?? "")

    );



    setMatrixA((prev: string[][]) =>

      Array.from({ length: newConstraints }, (_, i) =>

        Array.from({ length: newVars }, (__, j) => prev[i]?.[j] ?? "")

      )

    );



    setRhsB((prev: string[]) =>

      Array.from({ length: newConstraints }, (_, i) => prev[i] ?? "")

    );



    setInequalities((prev: Inequality[]) =>

      Array.from({ length: newConstraints }, (_, i) => prev[i] ?? "<=")

    );

  };



  // 4. Input Change Handlers

  const updateObjCoeff = (colIdx: number, val: string): void => {

    const updated = [...objCoeffs];

    updated[colIdx] = val;

    setObjCoeffs(updated);

  };



  const updateMatrixCell = (

    rowIdx: number,

    colIdx: number,

    val: string

  ): void => {

    const updated = matrixA.map((row) => [...row]);

    updated[rowIdx][colIdx] = val;

    setMatrixA(updated);

  };



  const updateRhs = (rowIdx: number, val: string): void => {

    const updated = [...rhsB];

    updated[rowIdx] = val;

    setRhsB(updated);

  };



  const updateInequality = (rowIdx: number, val: Inequality): void => {

    const updated = [...inequalities];

    updated[rowIdx] = val;

    setInequalities(updated);

  };



  // 5. Clear & Randomize Utilities

  const handleClear = (): void => {

    setObjCoeffs(Array(numVars).fill(""));

    setMatrixA(

      Array.from({ length: numConstraints }, () => Array(numVars).fill(""))

    );

    setRhsB(Array(numConstraints).fill(""));

    setInequalities(Array(numConstraints).fill("<="));

    setResult(null);

    setErrorMsg(null);

  };



  const handleRandomize = (): void => {

    const randInt = (): string => String(Math.floor(Math.random() * 11)); // 0 to 10

    setObjCoeffs(Array.from({ length: numVars }, randInt));

    setMatrixA(

      Array.from({ length: numConstraints }, () =>

        Array.from({ length: numVars }, randInt)

      )

    );

    setRhsB(Array.from({ length: numConstraints }, randInt));

    setErrorMsg(null);

  };



  // 6. Core Solver API Call (supports silent auto-solve on Max/Min toggle)

  const executeSolve = async (

    overrideMaximize?: boolean,

    silent: boolean = false

  ): Promise<void> => {

    const isMax: boolean =

      overrideMaximize !== undefined ? overrideMaximize : maximize;



    // Validate all cells are valid numbers

    const parsedC: number[] = objCoeffs.map((v) => Number(v));

    const parsedA: number[][] = matrixA.map((row) =>

      row.map((v) => Number(v))

    );

    const parsedB: number[] = rhsB.map((v) => Number(v));



    const hasEmptyOrNaN: boolean =

      objCoeffs.some((v) => v.trim() === "" || Number.isNaN(Number(v))) ||

      matrixA.some((row) =>

        row.some((v) => v.trim() === "" || Number.isNaN(Number(v)))

      ) ||

      rhsB.some((v) => v.trim() === "" || Number.isNaN(Number(v)));



    if (hasEmptyOrNaN) {

      if (!silent) {

        setErrorMsg("Please fill in all fields with valid numeric values.");

      }

      return;

    }



    setLoading(true);

    setErrorMsg(null);



    const payload: SimplexRequestPayload = {

      c: parsedC,

      A: parsedA,

      b: parsedB,

      inequalities,

      maximize: isMax,

    };



    try {

      const response = await fetch(`${API_BASE_URL}/solve`, {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify(payload),

      });



      if (!response.ok) {

        const errData = await response.json();

        throw new Error(errData.detail || "Server error occurred.");

      }



      const data: SimplexResponseData = await response.json();

      setResult(data);

    } catch (err: unknown) {

      if (!silent) {

        setErrorMsg(

          err instanceof Error ? err.message : "Could not connect to backend."

        );

      }

    } finally {

      setLoading(false);

    }

  };



  const handleObjectiveToggle = (newMaximize: boolean): void => {

    setMaximize(newMaximize);

    // Silently re-solve if inputs are already filled in

    void executeSolve(newMaximize, true);

  };



  return (

    <div className="app-container">

      <header className="app-header">

        <h1>Revised Simplex & Big-M Solver</h1>

        <p>Full-Stack FastAPI (Python 3.12) + React & TypeScript</p>

      </header>



      <main className="main-grid">

        {/* LEFT COLUMN: Controls & Matrix Input */}

        <section className="card input-panel">

          <h2>Problem Configuration</h2>



          <div className="config-row">

            <label>

              Dimension:

              <select

                value={numVars}

                onChange={(e) =>

                  handleResizeGrid(Number(e.target.value), numConstraints)

                }

              >

                <option value={2}>2D (x₁, x₂)</option>

                <option value={3}>3D (x₁, x₂, x₃)</option>

              </select>

            </label>



            <label>

              Constraints:

              <select

                value={numConstraints}

                onChange={(e) =>

                  handleResizeGrid(numVars, Number(e.target.value))

                }

              >

                {[2, 3, 4, 5, 6, 7, 8].map((n) => (

                  <option key={n} value={n}>

                    {n} Constraints

                  </option>

                ))}

              </select>

            </label>

          </div>



          <div className="radio-group">

            <span>Goal:</span>

            <label>

              <input

                type="radio"

                checked={maximize}

                onChange={() => handleObjectiveToggle(true)}

              />

              Maximize Z

            </label>

            <label>

              <input

                type="radio"

                checked={!maximize}

                onChange={() => handleObjectiveToggle(false)}

              />

              Minimize Z

            </label>

          </div>



          {/* Objective Function Row */}

          <div className="matrix-section">

            <h3>Objective Function (Z)</h3>

            <div className="equation-row">

              <span className="eq-label">{maximize ? "Max" : "Min"} Z =</span>

              {objCoeffs.map((val, j) => (

                <React.Fragment key={`obj-${j}`}>

                  <input

                    type="number"

                    step="any"

                    className="coeff-input"

                    value={val}

                    onChange={(e) => updateObjCoeff(j, e.target.value)}

                    placeholder="0"

                  />

                  <span className="var-label">

                    x<sub>{j + 1}</sub>

                    {j < numVars - 1 ? " +" : ""}

                  </span>

                </React.Fragment>

              ))}

            </div>

          </div>



          {/* Constraints Matrix */}

          <div className="matrix-section">

            <h3>Subject to Constraints</h3>

            <div className="constraints-list">

              {matrixA.map((row, i) => (

                <div className="equation-row" key={`row-${i}`}>

                  {row.map((val, j) => (

                    <React.Fragment key={`cell-${i}-${j}`}>

                      <input

                        type="number"

                        step="any"

                        className="coeff-input"

                        value={val}

                        onChange={(e) =>

                          updateMatrixCell(i, j, e.target.value)

                        }

                        placeholder="0"

                      />

                      <span className="var-label">

                        x<sub>{j + 1}</sub>

                        {j < numVars - 1 ? " +" : ""}

                      </span>

                    </React.Fragment>

                  ))}



                  <select

                    className="ineq-select"

                    value={inequalities[i]}

                    onChange={(e) =>

                      updateInequality(i, e.target.value as Inequality)

                    }

                  >

                    <option value="<=">&le;</option>

                    <option value=">=">&ge;</option>

                  </select>



                  <input

                    type="number"

                    step="any"

                    className="coeff-input rhs-input"

                    value={rhsB[i]}

                    onChange={(e) => updateRhs(i, e.target.value)}

                    placeholder="RHS"

                  />

                </div>

              ))}

            </div>

          </div>



          {errorMsg && <div className="error-banner">{errorMsg}</div>}



          <div className="action-buttons">

            <button

              className="btn btn-primary"

              onClick={() => void executeSolve()}

              disabled={loading}

            >

              {loading ? "Solving..." : "Solve Simplex"}

            </button>

            <button

              className="btn btn-secondary"

              type="button"

              onClick={handleRandomize}

            >

              Randomize (0–10)

            </button>

            <button

              className="btn btn-outline"

              type="button"

              onClick={handleClear}

            >

              Clear Inputs

            </button>

          </div>

        </section>



        {/* RIGHT COLUMN: Results & Matplotlib Visualization */}

        <section className="card output-panel">

          <h2>Results & Visualization</h2>



          {!result ? (

            <div className="empty-state">

              Enter your objective function and constraints, then click{" "}

              <strong>Solve Simplex</strong> to view the optimal solution and

              feasible region.

            </div>

          ) : (

            <div className="results-content">

              <div

                className={`status-badge ${

                  result.status.includes("Optimal")

                    ? "status-ok"

                    : "status-warn"

                }`}

              >

                {result.status}

              </div>



              <div className="metrics-grid">

                <div className="metric-box">

                  <span className="metric-label">Optimal Z*</span>

                  <span className="metric-value">{result.optimal_z}</span>

                </div>

                <div className="metric-box">

                  <span className="metric-label">Decision Variables</span>

                  <span className="metric-value">

                    {result.optimal_variables

                      .map((v, idx) => `x${idx + 1} = ${v}`)

                      .join(", ")}

                  </span>

                </div>

                <div className="metric-box">

                  <span className="metric-label">Execution Time</span>

                  <span className="metric-value">

                    {result.execution_time_ms} ms

                  </span>

                </div>

              </div>



              <div className="plot-container">

                {result.plot_base64 ? (

                  <img

                    src={`data:image/png;base64,${result.plot_base64}`}

                    alt="2D Feasible Region Plot"

                    className="feasible-plot"

                  />

                ) : (

                  <div className="no-plot-notice">

                    {numVars === 3

                      ? "3D problem solved mathematically! (2D Feasible Region plot is only displayed for 2-variable problems)."

                      : "No feasible region plot available for unbounded or infeasible solutions."}

                  </div>

                )}

              </div>

            </div>

          )}

        </section>

      </main>

    </div>

  );

}