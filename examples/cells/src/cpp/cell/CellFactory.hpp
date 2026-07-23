#ifndef CELLFACTORY_HPP_
#define CELLFACTORY_HPP_

/**
 * A minimal, header-only factory templated on a cell type.CELL_TYPE is used
 * only in the inline method bodies and never appears in the wrapped interface,
 * so cppwg sees it only as a template argument of the CellFactory<Cell, DIM>
 * instantiations - not in any signature. With auto_includes enabled, cppwg
 * resolves CELL_TYPE's header (Cell.hpp) from those template arguments, so the
 * generated wrapper - which odr-uses CreateCell and therefore needs the complete
 * CELL_TYPE - compiles.
 */
template <class CELL_TYPE, unsigned DIM>
class CellFactory
{
public:
    /**
     * Default Constructor
     */
    CellFactory() : mNumCells(0u)
    {
    }

    /**
     * Return the spatial dimension this factory builds in.
     */
    unsigned GetDimension() const
    {
        return DIM;
    }

    /**
     * Build one cell of CELL_TYPE and return the running total. Constructing a
     * CELL_TYPE here is what makes the wrapper need CELL_TYPE's header.
     */
    unsigned CreateCell()
    {
        CELL_TYPE cell;
        static_cast<void>(cell);
        return ++mNumCells;
    }

private:
    /** Number of cells created so far. */
    unsigned mNumCells;
};

#endif // CELLFACTORY_HPP_
