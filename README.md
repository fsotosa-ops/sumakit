# sumakit

Utilidades de EDA y analítica reutilizables: tablas de perfilado, diagnóstico
estadístico y gráficos con un tema consistente y re-skineable.

```python
from sumakit import nb, profile, stats, plots

nb.setup(seed=42)

profile.overview(df)                  # tipos, nulos, únicos, ceros, constantes
stats.distribution_report(df)         # asimetría, outliers y escalador sugerido
stats.high_correlation_pairs(df)      # colinealidad, sin entrecerrar los ojos

fig = plots.correlation_heatmap(df)   # devuelve Figure
fig.savefig("correlaciones.svg")      # sirve en notebook, informe y lámina
```

## Tres reglas

1. **Los gráficos devuelven `Figure`; ninguno llama a `plt.show()`.** La misma
   función sirve en el notebook, en el PDF y en un test.
2. **Nada muta estado global.** El tema se aplica una vez, o por bloque con
   `theme.using(...)`.
3. **Ninguna función trae paleta propia.** Todo sale del tema activo.

## Re-skinear por cliente

```python
from sumakit import theme
marca = theme.Palette(name="cliente", categorical=(...), ...)
theme.use(marca)
```

La paleta por defecto está validada para daltonismo y contraste. Las formas que
comparan todos los pares a la vez (scatter, pairplot) admiten un máximo de 3
series: pasado ese límite `theme.categorical()` levanta un error en vez de
generar colores indistinguibles.

## Instalación

```bash
pip install git+https://github.com/<usuario>/sumakit.git      # también en Colab
pip install "sumakit[ml] @ git+https://github.com/<usuario>/sumakit.git"
```

`[ml]` agrega scikit-learn, que habilita la información mutua en
`stats.target_report`.
